"""Deployment engine for managing KrakenD configuration deployments.

This module provides a unified interface for deploying configurations to KrakenD,
with support for both Docker Compose (local development) and Kubernetes (production)
environments.

The engine automatically detects the runtime environment and delegates to the
appropriate implementation:
- Docker mode: Uses HTTP-based health checks and file-based config deployment
- Kubernetes mode: Uses K8s API for ConfigMap management and pod monitoring

Config generation works by merging:
1. Base config (from krakend.json / Helm ConfigMap) — always preserved
2. Dynamic routes from approved exposures — appended alongside base routes
"""
import copy
from datetime import datetime
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.runtime import RUNTIME_MODE, RuntimeMode
from app.core.events import event_bus, EventType, emit_deployment_event
from app.modules.gateway.models import (
    Exposure,
    Deployment,
    ConfigVersion,
    ExposureChange,
    EventLog,
    DiscoveredResource,
)
from app.modules.gateway.generators import GeneratorRegistry


class DeploymentBackend(Protocol):
    """Protocol for deployment backend implementations."""

    async def get_health_details(self) -> dict[str, Any]: ...
    async def health_check(self) -> bool: ...
    async def update_config(self, config: dict[str, Any], version: int) -> str: ...
    async def rolling_restart(self) -> bool: ...
    async def wait_for_rollout(self, timeout: int = 120) -> bool: ...
    async def get_base_config(self) -> dict[str, Any] | None: ...


class DeploymentEngine:
    """
    Engine for deploying configurations to KrakenD gateway.

    Automatically detects runtime environment and uses appropriate backend:
    - Docker: File-based config with HTTP health checks
    - Kubernetes: ConfigMap-based config with K8s API

    All deployment logic (aggregation, config generation, version tracking)
    is shared across backends.
    """

    def __init__(self):
        """Initialize deployment engine with appropriate backend."""
        self.generator_registry = GeneratorRegistry()
        self._backend: DeploymentBackend = self._create_backend()

    def _create_backend(self) -> DeploymentBackend:
        """Create the appropriate backend based on runtime mode."""
        if RUNTIME_MODE == RuntimeMode.KUBERNETES:
            from app.modules.gateway.services.deployment_kubernetes import KubernetesDeploymentEngine
            return KubernetesDeploymentEngine()
        else:
            from app.modules.gateway.services.deployment_docker import DockerDeploymentEngine
            return DockerDeploymentEngine()

    async def get_health_details(self) -> dict[str, Any]:
        """Get detailed health information for dashboard and monitoring."""
        return await self._backend.get_health_details()

    async def health_check(self) -> bool:
        """Check if KrakenD is healthy."""
        return await self._backend.health_check()

    async def aggregate_approved_exposures(self, db: AsyncSession) -> list[Exposure]:
        """Get all approved exposures that should be deployed."""
        query = select(Exposure).where(Exposure.status == "approved")
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_base_config(self) -> dict[str, Any]:
        """
        Get the base KrakenD configuration (platform service routes).

        Reads from the deployment backend (file for Docker, ConfigMap for K8s).
        Falls back to a minimal config if the base can't be read.
        """
        base = await self._backend.get_base_config()
        if base:
            return base

        # Minimal fallback — should not normally be needed
        return {
            "version": 3,
            "name": "ES1 Platform API Gateway",
            "timeout": "30s",
            "cache_ttl": "300s",
            "output_encoding": "json",
            "endpoints": [],
            "extra_config": {},
        }

    async def generate_complete_config(
        self, exposures: list[Exposure], db: AsyncSession
    ) -> dict[str, Any]:
        """
        Generate complete KrakenD configuration by merging base routes with
        exposure-generated dynamic routes.

        Base routes (from krakend.json / Helm ConfigMap) are always preserved.
        Exposure routes are appended alongside them, never replacing them.
        Each endpoint is tagged with @managed_by to indicate its origin.
        """
        # Start from the real base config
        base_config = await self.get_base_config()
        krakend_config = copy.deepcopy(base_config)

        # Tag all base endpoints
        for endpoint in krakend_config.get("endpoints", []):
            endpoint["@managed_by"] = "base"

        # Generate and append dynamic endpoint configurations for each exposure
        for exposure in exposures:
            try:
                # Get the resource for this exposure
                resource_query = select(DiscoveredResource).where(
                    DiscoveredResource.id == exposure.resource_id
                )
                resource_result = await db.execute(resource_query)
                resource = resource_result.scalar_one_or_none()

                if not resource:
                    continue

                # Generate endpoint config using appropriate generator
                endpoint_config = self.generator_registry.generate_config(
                    resource_id=str(resource.id),
                    resource_type=resource.type,
                    resource_metadata=resource.resource_metadata,
                    settings=exposure.settings,
                )

                # Convert to dict and add to endpoints
                endpoint_dict = endpoint_config.model_dump(exclude_none=True)

                # Handle method field (can be string or list)
                if isinstance(endpoint_dict.get("method"), list):
                    endpoint_dict["method"] = ",".join(endpoint_dict["method"])

                # Tag as platform-manager managed
                endpoint_dict["@managed_by"] = "platform-manager"
                endpoint_dict["@exposure_id"] = str(exposure.id)
                endpoint_dict["@resource_type"] = resource.type
                endpoint_dict["@resource_source"] = resource.source

                krakend_config["endpoints"].append(endpoint_dict)

            except Exception as e:
                print(f"Error generating config for exposure {exposure.id}: {e}")
                continue

        return krakend_config

    async def get_config_state(self, db: AsyncSession) -> dict[str, Any]:
        """
        Get the complete state of the gateway configuration.

        Returns the full picture: active version, global config, base routes,
        dynamic routes, and counts — everything needed for the Overview tab.
        """
        # Get the active config version from DB
        query = select(ConfigVersion).where(ConfigVersion.is_active == True)
        result = await db.execute(query)
        active_version = result.scalar_one_or_none()

        # Get the base config
        base_config = await self.get_base_config()
        base_endpoints = base_config.get("endpoints", [])

        # Get deployed exposures with their resources
        deployed_query = (
            select(Exposure, DiscoveredResource)
            .join(DiscoveredResource, Exposure.resource_id == DiscoveredResource.id)
            .where(Exposure.status == "deployed")
        )
        deployed_result = await db.execute(deployed_query)
        deployed_pairs = deployed_result.all()

        # Build base routes info
        base_routes = []
        for ep in base_endpoints:
            route_info = {
                "endpoint": ep.get("endpoint", ""),
                "method": ep.get("method", ""),
                "managed_by": "base",
            }
            # Extract backend host
            backends = ep.get("backend", [])
            if backends:
                hosts = backends[0].get("host", [])
                route_info["backend_host"] = hosts[0] if hosts else ""
                route_info["url_pattern"] = backends[0].get("url_pattern", "")
            # Extract comment as description
            if "@comment" in ep:
                route_info["description"] = ep["@comment"]
            base_routes.append(route_info)

        # Build dynamic routes info
        dynamic_routes = []
        for exposure, resource in deployed_pairs:
            generated = exposure.generated_config or {}
            dynamic_routes.append({
                "endpoint": generated.get("endpoint", ""),
                "method": generated.get("method", ""),
                "resource_type": resource.type,
                "resource_source": resource.source,
                "resource_name": resource.resource_metadata.get("name", resource.source_id),
                "exposure_id": str(exposure.id),
                "managed_by": "platform-manager",
                "settings": exposure.settings,
            })

        # Build global config (everything except endpoints)
        global_config = {}
        for key in ["timeout", "cache_ttl", "output_encoding", "port"]:
            if key in base_config:
                global_config[key] = base_config[key]
        extra = base_config.get("extra_config", {})
        if "security/cors" in extra:
            global_config["cors"] = extra["security/cors"]
        if "telemetry/opencensus" in extra:
            global_config["telemetry"] = extra["telemetry/opencensus"]

        return {
            "active_version": active_version.version if active_version else None,
            "deployed_at": (
                active_version.deployed_to_gateway_at.isoformat()
                if active_version and active_version.deployed_to_gateway_at
                else None
            ),
            "deployed_by": active_version.created_by if active_version else None,
            "global_config": global_config,
            "base_routes": base_routes,
            "dynamic_routes": dynamic_routes,
            "total_endpoints": len(base_endpoints) + len(dynamic_routes),
            "base_endpoint_count": len(base_endpoints),
            "dynamic_endpoint_count": len(dynamic_routes),
        }

    async def deploy(
        self, db: AsyncSession, deployed_by: str, commit_message: str | None = None
    ) -> tuple[bool, str, str | None]:
        """
        Execute full deployment workflow.

        Returns:
            tuple: (success: bool, message: str, deployment_id: str | None)
        """
        deployment_id = None

        try:
            # Emit deployment started event
            await emit_deployment_event(
                EventType.DEPLOYMENT_STARTED,
                deployment_id="pending",
                message="Starting deployment...",
            )

            # 1. Aggregate approved exposures
            exposures = await self.aggregate_approved_exposures(db)

            # 2. Generate complete configuration (base + exposures)
            config = await self.generate_complete_config(exposures, db)

            # 3. Get next version number
            next_version = await self._get_next_version(db)

            # 4. Save configuration version
            config_version = ConfigVersion(
                version=next_version,
                config_snapshot=config,
                created_by=deployed_by,
                commit_message=commit_message or f"Deploy {len(exposures)} exposures",
            )
            db.add(config_version)
            await db.flush()

            # 5. Create deployment record
            deployment = Deployment(
                version_id=config_version.id,
                status="in_progress",
                deployed_by=deployed_by,
            )
            db.add(deployment)
            await db.commit()
            await db.refresh(deployment)
            deployment_id = str(deployment.id)

            # Emit progress event
            await emit_deployment_event(
                EventType.DEPLOYMENT_PROGRESS,
                deployment_id=deployment_id,
                version=next_version,
                message="Updating gateway configuration...",
                details={"progress": 50},
            )

            # 6. Update config via backend (ConfigMap or file)
            try:
                await self._backend.update_config(config, next_version)
            except Exception as e:
                deployment.status = "failed"
                deployment.error_message = f"Failed to update config: {str(e)}"
                await db.commit()
                await emit_deployment_event(
                    EventType.DEPLOYMENT_FAILED,
                    deployment_id=deployment_id,
                    message=f"Failed to update config: {str(e)}",
                )
                return (False, f"Failed to update config: {str(e)}", deployment_id)

            # 7. Trigger rolling restart (if applicable)
            if hasattr(self._backend, 'rolling_restart'):
                if not await self._backend.rolling_restart():
                    deployment.status = "failed"
                    deployment.error_message = "Failed to restart deployment"
                    await db.commit()
                    await emit_deployment_event(
                        EventType.DEPLOYMENT_FAILED,
                        deployment_id=deployment_id,
                        message="Failed to restart KrakenD",
                    )
                    return (False, "Failed to restart KrakenD", deployment_id)

            # 8. Wait for rollout (if applicable)
            if hasattr(self._backend, 'wait_for_rollout'):
                if not await self._backend.wait_for_rollout():
                    deployment.status = "failed"
                    deployment.error_message = "Deployment rollout timeout"
                    await db.commit()
                    await emit_deployment_event(
                        EventType.DEPLOYMENT_FAILED,
                        deployment_id=deployment_id,
                        message="Deployment rollout timeout",
                    )
                    return (False, "Deployment rollout timeout", deployment_id)
            else:
                # Docker mode: wait for health check
                if hasattr(self._backend, 'wait_for_ready'):
                    if not await self._backend.wait_for_ready():
                        deployment.status = "failed"
                        deployment.error_message = "KrakenD not ready after config update"
                        await db.commit()
                        return (False, "KrakenD not ready", deployment_id)

            # 9. Health check
            if not await self._backend.health_check():
                deployment.status = "failed"
                deployment.error_message = "Health check failed"
                deployment.health_check_passed = False
                await db.commit()
                await emit_deployment_event(
                    EventType.DEPLOYMENT_FAILED,
                    deployment_id=deployment_id,
                    message="Health check failed",
                )
                return (False, "Health check failed", deployment_id)

            # 10. Mark deployment as successful
            deployment.status = "succeeded"
            deployment.health_check_passed = True
            deployment.completed_at = datetime.utcnow()

            # Update exposure statuses to deployed
            for exposure in exposures:
                exposure.status = "deployed"
                exposure.deployed_in_version_id = config_version.id

            # Mark old config versions as inactive
            old_versions_query = select(ConfigVersion).where(ConfigVersion.is_active == True)
            old_versions_result = await db.execute(old_versions_query)
            for old_version in old_versions_result.scalars().all():
                old_version.is_active = False

            # Mark new config version as active
            config_version.is_active = True
            config_version.deployed_to_gateway_at = datetime.utcnow()

            # Log deployment event
            event = EventLog(
                event_type="deployment_succeeded",
                entity_type="deployment",
                entity_id=deployment.id,
                user_id=deployed_by,
                event_metadata={
                    "version_id": str(config_version.id),
                    "version": config_version.version,
                    "exposures_count": len(exposures),
                    "commit_message": commit_message or f"Deploy {len(exposures)} exposures",
                    "runtime_mode": RUNTIME_MODE.value,
                },
            )
            db.add(event)

            await db.commit()

            # Emit success event
            await emit_deployment_event(
                EventType.DEPLOYMENT_COMPLETED,
                deployment_id=deployment_id,
                version=next_version,
                message=f"Successfully deployed {len(exposures)} exposures",
                details={"exposures_count": len(exposures)},
            )

            return (
                True,
                f"Successfully deployed {len(exposures)} exposures",
                deployment_id,
            )

        except Exception as e:
            # Mark deployment as failed if we have a deployment record
            if deployment_id:
                deployment_query = select(Deployment).where(Deployment.id == deployment_id)
                result = await db.execute(deployment_query)
                deployment = result.scalar_one_or_none()
                if deployment:
                    deployment.status = "failed"
                    deployment.error_message = str(e)

                    event = EventLog(
                        event_type="deployment_failed",
                        entity_type="deployment",
                        entity_id=deployment.id,
                        user_id=deployed_by,
                        event_metadata={"error": str(e)}
                    )
                    db.add(event)
                    await db.commit()

            await emit_deployment_event(
                EventType.DEPLOYMENT_FAILED,
                deployment_id=deployment_id or "unknown",
                message=f"Deployment failed: {str(e)}",
            )

            return (False, f"Deployment failed: {str(e)}", deployment_id)

    async def _get_next_version(self, db: AsyncSession) -> int:
        """Get the next configuration version number."""
        query = select(ConfigVersion).order_by(ConfigVersion.version.desc()).limit(1)
        result = await db.execute(query)
        latest = result.scalar_one_or_none()

        if latest:
            return latest.version + 1
        return 1

    async def get_current_config(self) -> dict[str, Any] | None:
        """Get the currently deployed configuration from the gateway."""
        if hasattr(self._backend, 'get_current_config'):
            return await self._backend.get_current_config()
        return None

    async def list_config_files(self) -> list[dict[str, Any]]:
        """List available configuration files from the backend."""
        if hasattr(self._backend, 'list_config_versions'):
            return await self._backend.list_config_versions()
        return []
