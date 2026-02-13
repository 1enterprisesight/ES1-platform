"""Kubernetes-specific deployment engine for production environments."""
import json
import asyncio
from datetime import datetime
from typing import Any

from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException

from app.core.config import settings


class KubernetesDeploymentEngine:
    """
    Deployment engine for Kubernetes environment.

    Uses Kubernetes API for:
    - Versioned ConfigMap deployment (enables rollback)
    - Deployment rolling restart
    - Pod health monitoring
    """

    def __init__(self):
        """Initialize Kubernetes deployment engine."""
        # Load Kubernetes config
        try:
            k8s_config.load_incluster_config()
        except k8s_config.ConfigException:
            # Fall back to kubeconfig for local development
            k8s_config.load_kube_config()

        self.core_api = client.CoreV1Api()
        self.apps_api = client.AppsV1Api()

        # Use settings instead of hardcoded values
        self.namespace = settings.KRAKEND_NAMESPACE
        self.configmap_name = settings.KRAKEND_CONFIGMAP_NAME
        self.deployment_name = settings.KRAKEND_DEPLOYMENT_NAME
        self.label_selector = settings.KRAKEND_LABEL_SELECTOR
        self.retention_count = settings.CONFIGMAP_RETENTION_COUNT
        self.managed_by_label = settings.KRAKEND_MANAGED_BY_LABEL
        self.annotation_domain = settings.ANNOTATION_DOMAIN
        # Compose ConfigMap selector from settings (for managed config versions)
        self.configmap_selector = f"managed-by={self.managed_by_label},app=krakend"

    async def get_health_details(self) -> dict[str, Any]:
        """
        Get detailed health information from Kubernetes pod status.

        Returns:
            dict: Health status with pod counts and status
        """
        try:
            # List pods for the deployment
            pods = await asyncio.to_thread(
                self.core_api.list_namespaced_pod,
                namespace=self.namespace,
                label_selector=self.label_selector,
            )

            total_pods = len(pods.items)
            running_pods = sum(
                1 for pod in pods.items if pod.status.phase == "Running"
            )
            failed_health_checks = total_pods - running_pods

            # Determine overall health status
            if running_pods == total_pods and total_pods > 0:
                status = "healthy"
            elif running_pods > 0:
                status = "degraded"
            else:
                status = "unhealthy"

            return {
                "status": status,
                "pod_count": total_pods,
                "running_pods": running_pods,
                "failed_health_checks": failed_health_checks,
                "mode": "kubernetes",
                "namespace": self.namespace,
            }

        except ApiException as e:
            return {
                "status": "unhealthy",
                "pod_count": 0,
                "running_pods": 0,
                "failed_health_checks": 0,
                "mode": "kubernetes",
                "error": f"Kubernetes API error: {e.reason}",
            }

    async def health_check(self) -> bool:
        """
        Check if KrakenD pods are healthy.

        Returns:
            bool: True if all pods are ready, False otherwise
        """
        try:
            pods = await asyncio.to_thread(
                self.core_api.list_namespaced_pod,
                namespace=self.namespace,
                label_selector=self.label_selector,
            )

            if not pods.items:
                return False

            for pod in pods.items:
                if pod.status.phase != "Running":
                    return False

                if pod.status.container_statuses:
                    for container in pod.status.container_statuses:
                        if not container.ready:
                            return False

            return True

        except ApiException:
            return False

    async def get_base_config(self) -> dict[str, Any] | None:
        """
        Get the base KrakenD configuration from the Helm-managed ConfigMap.

        This is the base `krakend-config` ConfigMap (NOT a versioned one like
        `krakend-config-v3`). It contains the platform service routes that
        should always be present.

        Returns:
            dict: Base config if ConfigMap exists, None otherwise
        """
        try:
            configmap = await asyncio.to_thread(
                self.core_api.read_namespaced_config_map,
                name=self.configmap_name,
                namespace=self.namespace,
            )
            config_data = configmap.data.get("krakend.json")
            if config_data:
                return json.loads(config_data)
            return None
        except ApiException:
            return None

    async def get_current_config(self) -> dict[str, Any] | None:
        """
        Get the currently deployed configuration from KrakenD ConfigMap.

        Returns:
            dict: Current config if ConfigMap exists, None otherwise
        """
        try:
            # Get the deployment to find which ConfigMap is mounted
            deployment = await asyncio.to_thread(
                self.apps_api.read_namespaced_deployment,
                name=self.deployment_name,
                namespace=self.namespace,
            )

            # Find the ConfigMap name from volumes
            configmap_name = None
            for volume in deployment.spec.template.spec.volumes:
                if volume.config_map and volume.config_map.name.startswith(self.configmap_name):
                    configmap_name = volume.config_map.name
                    break

            if not configmap_name:
                # Fall back to the base configmap name
                configmap_name = f"{self.configmap_name}-config"

            # Read the ConfigMap
            configmap = await asyncio.to_thread(
                self.core_api.read_namespaced_config_map,
                name=configmap_name,
                namespace=self.namespace,
            )

            # Parse the krakend.json content
            config_data = configmap.data.get("krakend.json")
            if config_data:
                return json.loads(config_data)

            return None

        except ApiException as e:
            print(f"Error reading current config: {e}")
            return None

    async def update_config(self, config: dict[str, Any], version: int) -> str:
        """
        Deploy config as a versioned ConfigMap.

        Creates a new ConfigMap with version suffix, enabling:
        - Full history of configurations
        - Instant rollback by changing deployment reference
        - Audit trail of changes

        Args:
            config: The complete KrakenD configuration
            version: The configuration version number

        Returns:
            str: Name of the created ConfigMap
        """
        versioned_name = f"{self.configmap_name}-v{version}"
        config_json = json.dumps(config, indent=2)

        configmap = client.V1ConfigMap(
            metadata=client.V1ObjectMeta(
                name=versioned_name,
                namespace=self.namespace,
                labels={
                    "app": "krakend",
                    "config-version": str(version),
                    "managed-by": self.managed_by_label,
                },
                annotations={
                    f"{self.annotation_domain}/created-at": datetime.utcnow().isoformat(),
                },
            ),
            data={"krakend.json": config_json},
        )

        try:
            await asyncio.to_thread(
                self.core_api.create_namespaced_config_map,
                namespace=self.namespace,
                body=configmap,
            )
        except ApiException as e:
            if e.status == 409:
                # ConfigMap already exists, update it
                await asyncio.to_thread(
                    self.core_api.replace_namespaced_config_map,
                    name=versioned_name,
                    namespace=self.namespace,
                    body=configmap,
                )
            else:
                raise

        # Update deployment to reference new ConfigMap
        await self._update_deployment_configmap_ref(versioned_name)

        # Cleanup old ConfigMaps beyond retention limit
        await self._cleanup_old_configmaps()

        return versioned_name

    async def _update_deployment_configmap_ref(self, configmap_name: str) -> None:
        """
        Update deployment to reference a specific ConfigMap.

        This changes the volume mount to point to the new ConfigMap,
        triggering a rolling update.

        Args:
            configmap_name: Name of the ConfigMap to reference
        """
        try:
            deployment = await asyncio.to_thread(
                self.apps_api.read_namespaced_deployment,
                name=self.deployment_name,
                namespace=self.namespace,
            )

            # Find and update the krakend-config volume
            for volume in deployment.spec.template.spec.volumes:
                if volume.config_map and volume.config_map.name.startswith(self.configmap_name):
                    volume.config_map.name = configmap_name
                    break

            # Also update restart annotation to ensure rollout
            if not deployment.spec.template.metadata.annotations:
                deployment.spec.template.metadata.annotations = {}

            deployment.spec.template.metadata.annotations[
                "kubectl.kubernetes.io/restartedAt"
            ] = datetime.utcnow().isoformat()

            await asyncio.to_thread(
                self.apps_api.replace_namespaced_deployment,
                name=self.deployment_name,
                namespace=self.namespace,
                body=deployment,
            )

        except ApiException as e:
            raise RuntimeError(f"Failed to update deployment: {e.reason}")

    async def _cleanup_old_configmaps(self) -> None:
        """
        Remove old ConfigMaps beyond the retention limit.

        Keeps the most recent N versions (configured via settings).
        Never deletes ConfigMaps that are currently in use.
        """
        try:
            # List all managed ConfigMaps
            configmaps = await asyncio.to_thread(
                self.core_api.list_namespaced_config_map,
                namespace=self.namespace,
                label_selector=self.configmap_selector,
            )

            # Sort by version number (descending)
            sorted_cms = sorted(
                configmaps.items,
                key=lambda cm: int(cm.metadata.labels.get("config-version", 0)),
                reverse=True,
            )

            # Get currently referenced ConfigMap from deployment
            current_cm = None
            try:
                deployment = await asyncio.to_thread(
                    self.apps_api.read_namespaced_deployment,
                    name=self.deployment_name,
                    namespace=self.namespace,
                )
                for volume in deployment.spec.template.spec.volumes:
                    if volume.config_map and volume.config_map.name.startswith(self.configmap_name):
                        current_cm = volume.config_map.name
                        break
            except ApiException:
                pass

            # Delete ConfigMaps beyond retention, but never delete current
            for cm in sorted_cms[self.retention_count:]:
                if cm.metadata.name == current_cm:
                    continue  # Never delete the active ConfigMap

                try:
                    await asyncio.to_thread(
                        self.core_api.delete_namespaced_config_map,
                        name=cm.metadata.name,
                        namespace=self.namespace,
                    )
                except ApiException:
                    pass  # Ignore deletion errors

        except ApiException:
            pass  # Cleanup is best-effort

    async def rolling_restart(self) -> bool:
        """
        Trigger a rolling restart of the KrakenD deployment.

        Returns:
            bool: True if restart triggered successfully
        """
        try:
            deployment = await asyncio.to_thread(
                self.apps_api.read_namespaced_deployment,
                name=self.deployment_name,
                namespace=self.namespace,
            )

            if not deployment.spec.template.metadata.annotations:
                deployment.spec.template.metadata.annotations = {}

            deployment.spec.template.metadata.annotations[
                "kubectl.kubernetes.io/restartedAt"
            ] = datetime.utcnow().isoformat()

            await asyncio.to_thread(
                self.apps_api.patch_namespaced_deployment,
                name=self.deployment_name,
                namespace=self.namespace,
                body=deployment,
            )

            return True

        except ApiException as e:
            print(f"Error restarting deployment: {e}")
            return False

    async def wait_for_rollout(self, timeout: int = 120) -> bool:
        """
        Wait for the deployment rollout to complete.

        Args:
            timeout: Maximum seconds to wait

        Returns:
            bool: True if rollout completed within timeout
        """
        try:
            start_time = datetime.utcnow()

            while True:
                deployment = await asyncio.to_thread(
                    self.apps_api.read_namespaced_deployment,
                    name=self.deployment_name,
                    namespace=self.namespace,
                )

                # Check if rollout is complete
                if (
                    deployment.status.updated_replicas == deployment.spec.replicas
                    and deployment.status.replicas == deployment.spec.replicas
                    and deployment.status.available_replicas == deployment.spec.replicas
                ):
                    return True

                # Check timeout
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed > timeout:
                    return False

                await asyncio.sleep(2)

        except ApiException as e:
            print(f"Error waiting for rollout: {e}")
            return False

    async def list_config_versions(self) -> list[dict[str, Any]]:
        """
        List available configuration versions from ConfigMaps.

        Returns:
            list: List of version info dicts
        """
        try:
            configmaps = await asyncio.to_thread(
                self.core_api.list_namespaced_config_map,
                namespace=self.namespace,
                label_selector=self.configmap_selector,
            )

            versions = []
            for cm in configmaps.items:
                version_num = int(cm.metadata.labels.get("config-version", 0))
                created_at = cm.metadata.annotations.get(
                    f"{self.annotation_domain}/created-at",
                    cm.metadata.creation_timestamp.isoformat() if cm.metadata.creation_timestamp else ""
                )

                versions.append({
                    "version": version_num,
                    "configmap": cm.metadata.name,
                    "created_at": created_at,
                    "namespace": self.namespace,
                })

            # Sort by version descending
            versions.sort(key=lambda v: v["version"], reverse=True)
            return versions

        except ApiException:
            return []

    async def rollback_to_version(self, version: int) -> bool:
        """
        Rollback to a previous configuration version.

        Args:
            version: Version number to rollback to

        Returns:
            bool: True if rollback successful
        """
        configmap_name = f"{self.configmap_name}-v{version}"

        try:
            # Verify ConfigMap exists
            await asyncio.to_thread(
                self.core_api.read_namespaced_config_map,
                name=configmap_name,
                namespace=self.namespace,
            )

            # Update deployment to reference this ConfigMap
            await self._update_deployment_configmap_ref(configmap_name)

            # Wait for rollout
            return await self.wait_for_rollout()

        except ApiException:
            return False
