"""Service for managing gateway configuration change sets.

A change set is a draft collection of configuration changes (add/remove/modify
exposures) that can be previewed, submitted for approval, and deployed as a unit.

The workflow:
1. Create a change set from current running config or a historical version
2. Add/remove/modify exposures within the change set
3. Preview the resulting config and diff
4. Submit for approval (creates a ConfigVersion with pending_approval status)
5. Approve/reject the config version
6. Deploy the approved config version
"""
import copy
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import event_bus, EventType
from app.modules.gateway.models import (
    ChangeSet,
    ExposureChange,
    Exposure,
    ConfigVersion,
    DiscoveredResource,
    EventLog,
)
from app.modules.gateway.generators import GeneratorRegistry
from app.modules.gateway.services.deployment_engine import DeploymentEngine


class ChangeSetService:
    """Service for creating and managing change sets."""

    def __init__(self):
        self.generator_registry = GeneratorRegistry()

    async def create_from_current(self, db: AsyncSession, user: str, description: str | None = None) -> ChangeSet:
        """
        Create a new change set using the current running config as baseline.

        base_version_id = None means "start from current running config."
        """
        change_set = ChangeSet(
            base_version_id=None,
            status="draft",
            created_by=user,
            description=description,
        )
        db.add(change_set)
        await db.commit()
        await db.refresh(change_set)

        # Audit
        db.add(EventLog(
            event_type="change_set_created",
            entity_type="change_set",
            entity_id=change_set.id,
            user_id=user,
            event_metadata={"base": "current", "description": description},
        ))
        await db.commit()

        await event_bus.publish(EventType.CHANGE_SET_CREATED, {
            "change_set_id": str(change_set.id),
            "base": "current",
            "created_by": user,
        })

        return change_set

    async def create_from_version(
        self, db: AsyncSession, version_id: UUID, user: str, description: str | None = None
    ) -> ChangeSet:
        """
        Create a new change set from a historical ConfigVersion.
        """
        # Verify version exists
        config_version = await db.get(ConfigVersion, version_id)
        if not config_version:
            raise ValueError(f"Config version {version_id} not found")

        change_set = ChangeSet(
            base_version_id=version_id,
            status="draft",
            created_by=user,
            description=description,
        )
        db.add(change_set)
        await db.commit()
        await db.refresh(change_set)

        # Audit
        db.add(EventLog(
            event_type="change_set_created",
            entity_type="change_set",
            entity_id=change_set.id,
            user_id=user,
            event_metadata={
                "base": "version",
                "base_version": config_version.version,
                "description": description,
            },
        ))
        await db.commit()

        await event_bus.publish(EventType.CHANGE_SET_CREATED, {
            "change_set_id": str(change_set.id),
            "base": f"version:{config_version.version}",
            "created_by": user,
        })

        return change_set

    async def add_resource(
        self, db: AsyncSession, change_set_id: UUID, resource_id: UUID, settings: dict[str, Any], user: str
    ) -> ExposureChange | None:
        """Add a resource to expose in this change set.

        If there's already a "remove" change for this resource in the same
        change set, cancels the remove instead (net zero = no change record).
        Returns None when a remove was cancelled.
        """
        change_set = await self._get_draft_change_set(db, change_set_id)

        # Verify resource exists
        resource = await db.get(DiscoveredResource, resource_id)
        if not resource:
            raise ValueError(f"Resource {resource_id} not found")

        # Check for opposing "remove" change for this resource — cancel it instead
        existing_remove = await self._find_change(db, change_set_id, "remove", resource_id=resource_id)
        if existing_remove:
            await db.delete(existing_remove)
            db.add(EventLog(
                event_type="change_set_change_cancelled",
                entity_type="change_set",
                entity_id=change_set_id,
                user_id=user,
                event_metadata={
                    "cancelled_change_id": str(existing_remove.id),
                    "reason": "add_cancels_remove",
                    "resource_id": str(resource_id),
                },
            ))
            await db.commit()
            return None

        change = ExposureChange(
            resource_id=resource_id,
            change_type="add",
            settings_after=settings,
            status="draft",
            change_set_id=change_set_id,
            requested_by=user,
        )
        db.add(change)
        await db.commit()
        await db.refresh(change)

        # Audit
        db.add(EventLog(
            event_type="change_set_resource_added",
            entity_type="change_set",
            entity_id=change_set_id,
            user_id=user,
            event_metadata={
                "change_id": str(change.id),
                "resource_id": str(resource_id),
                "resource_type": resource.type,
                "resource_source": resource.source,
                "settings": settings,
            },
        ))
        await db.commit()

        await event_bus.publish(EventType.CHANGE_SET_RESOURCE_ADDED, {
            "change_set_id": str(change_set_id),
            "change_id": str(change.id),
            "resource_id": str(resource_id),
        })

        return change

    async def remove_resource(
        self, db: AsyncSession, change_set_id: UUID,
        resource_id: UUID | None, exposure_id: UUID | None, user: str
    ) -> ExposureChange | None:
        """Mark a dynamic route for removal in this change set.

        Accepts resource_id (preferred) or exposure_id. If there's already
        an "add" change for this resource in the same change set, cancels
        the add instead (net zero). Returns None when an add was cancelled.
        """
        change_set = await self._get_draft_change_set(db, change_set_id)

        if not resource_id and not exposure_id:
            raise ValueError("Either resource_id or exposure_id is required")

        # Resolve resource_id from exposure_id if needed
        if not resource_id and exposure_id:
            exposure = await db.get(Exposure, exposure_id)
            if exposure:
                resource_id = exposure.resource_id

        if not resource_id:
            raise ValueError("Could not resolve resource_id")

        # Check for opposing "add" change for this resource — cancel it instead
        existing_add = await self._find_change(db, change_set_id, "add", resource_id=resource_id)
        if existing_add:
            await db.delete(existing_add)
            db.add(EventLog(
                event_type="change_set_change_cancelled",
                entity_type="change_set",
                entity_id=change_set_id,
                user_id=user,
                event_metadata={
                    "cancelled_change_id": str(existing_add.id),
                    "reason": "remove_cancels_add",
                    "resource_id": str(resource_id),
                },
            ))
            await db.commit()
            return None

        change = ExposureChange(
            exposure_id=exposure_id,
            resource_id=resource_id,
            change_type="remove",
            status="draft",
            change_set_id=change_set_id,
            requested_by=user,
        )
        db.add(change)
        await db.commit()
        await db.refresh(change)

        # Audit
        db.add(EventLog(
            event_type="change_set_exposure_removed",
            entity_type="change_set",
            entity_id=change_set_id,
            user_id=user,
            event_metadata={
                "change_id": str(change.id),
                "resource_id": str(resource_id),
                "exposure_id": str(exposure_id) if exposure_id else None,
            },
        ))
        await db.commit()

        await event_bus.publish(EventType.CHANGE_SET_EXPOSURE_REMOVED, {
            "change_set_id": str(change_set_id),
            "change_id": str(change.id),
            "resource_id": str(resource_id),
        })

        return change

    async def modify_settings(
        self, db: AsyncSession, change_set_id: UUID, exposure_id: UUID,
        new_settings: dict[str, Any], user: str
    ) -> ExposureChange:
        """Modify an existing exposure's settings in this change set."""
        change_set = await self._get_draft_change_set(db, change_set_id)

        # Verify exposure exists
        exposure = await db.get(Exposure, exposure_id)
        if not exposure:
            raise ValueError(f"Exposure {exposure_id} not found")

        change = ExposureChange(
            exposure_id=exposure_id,
            resource_id=exposure.resource_id,
            change_type="modify",
            settings_before=exposure.settings,
            settings_after=new_settings,
            status="draft",
            change_set_id=change_set_id,
            requested_by=user,
        )
        db.add(change)
        await db.commit()
        await db.refresh(change)

        # Audit
        db.add(EventLog(
            event_type="change_set_settings_modified",
            entity_type="change_set",
            entity_id=change_set_id,
            user_id=user,
            event_metadata={
                "change_id": str(change.id),
                "exposure_id": str(exposure_id),
                "settings_before": exposure.settings,
                "settings_after": new_settings,
            },
        ))
        await db.commit()

        await event_bus.publish(EventType.CHANGE_SET_SETTINGS_MODIFIED, {
            "change_set_id": str(change_set_id),
            "change_id": str(change.id),
            "exposure_id": str(exposure_id),
        })

        return change

    async def get_effective_config(self, db: AsyncSession, change_set_id: UUID) -> dict[str, Any]:
        """
        Compute what the config WOULD look like if this change set were deployed.

        Starts from the config SNAPSHOT (the actual deployed JSON), then applies
        add/remove/modify changes on top. The snapshot is the source of truth —
        not the exposures table.
        """
        change_set = await db.get(ChangeSet, change_set_id)
        if not change_set:
            raise ValueError(f"Change set {change_set_id} not found")

        # Get the baseline config snapshot
        if change_set.base_version_id:
            # Starting from a historical version
            base_version = await db.get(ConfigVersion, change_set.base_version_id)
            if not base_version or not base_version.config_snapshot:
                raise ValueError(f"Config version {change_set.base_version_id} has no snapshot")
            result_config = copy.deepcopy(base_version.config_snapshot)
        else:
            # Starting from current running config = active version's snapshot
            query = select(ConfigVersion).where(ConfigVersion.is_active == True)
            result = await db.execute(query)
            active = result.scalar_one_or_none()
            if active and active.config_snapshot:
                result_config = copy.deepcopy(active.config_snapshot)
            else:
                # No active version — fall back to base config only
                engine = DeploymentEngine()
                base_config = await engine.get_base_config()
                result_config = copy.deepcopy(base_config)
                for ep in result_config.get("endpoints", []):
                    ep["@managed_by"] = "base"

        # Apply changes from this change set
        changes = await self._get_changes(db, change_set_id)

        for change in changes:
            if change.change_type == "add":
                resource = await db.get(DiscoveredResource, change.resource_id)
                if resource:
                    try:
                        endpoint_config = self.generator_registry.generate_config(
                            resource_id=str(resource.id),
                            resource_type=resource.type,
                            resource_metadata=resource.resource_metadata,
                            settings=change.settings_after or {},
                        )
                        endpoint_dict = endpoint_config.model_dump(exclude_none=True)
                        if isinstance(endpoint_dict.get("method"), list):
                            endpoint_dict["method"] = ",".join(endpoint_dict["method"])
                        endpoint_dict["@managed_by"] = "platform-manager"
                        endpoint_dict["@resource_id"] = str(resource.id)
                        endpoint_dict["@resource_type"] = resource.type
                        endpoint_dict["@resource_source"] = resource.source
                        result_config["endpoints"].append(endpoint_dict)
                    except Exception:
                        pass

            elif change.change_type == "remove":
                # Remove from snapshot by resource_id match
                resource_id_str = str(change.resource_id) if change.resource_id else None
                exposure_id_str = str(change.exposure_id) if change.exposure_id else None
                result_config["endpoints"] = [
                    ep for ep in result_config.get("endpoints", [])
                    if not self._endpoint_matches_removal(ep, exposure_id_str, resource_id_str)
                ]

            elif change.change_type == "modify" and change.resource_id:
                # Re-generate and replace the matching endpoint
                resource = await db.get(DiscoveredResource, change.resource_id)
                if resource:
                    try:
                        endpoint_config = self.generator_registry.generate_config(
                            resource_id=str(resource.id),
                            resource_type=resource.type,
                            resource_metadata=resource.resource_metadata,
                            settings=change.settings_after or {},
                        )
                        new_ep = endpoint_config.model_dump(exclude_none=True)
                        if isinstance(new_ep.get("method"), list):
                            new_ep["method"] = ",".join(new_ep["method"])
                        new_ep["@managed_by"] = "platform-manager"
                        new_ep["@resource_id"] = str(resource.id)
                        new_ep["@resource_type"] = resource.type
                        new_ep["@resource_source"] = resource.source
                        new_ep["@modified"] = True

                        resource_id_str = str(resource.id)
                        result_config["endpoints"] = [
                            new_ep if ep.get("@resource_id") == resource_id_str else ep
                            for ep in result_config.get("endpoints", [])
                        ]
                    except Exception:
                        pass

        return result_config

    @staticmethod
    def _endpoint_matches_removal(
        endpoint: dict[str, Any], exposure_id: str | None, resource_id: str | None
    ) -> bool:
        """Check if an endpoint should be removed. Only removes platform-manager routes."""
        if endpoint.get("@managed_by") != "platform-manager":
            return False
        if exposure_id and endpoint.get("@exposure_id") == exposure_id:
            return True
        if resource_id and endpoint.get("@resource_id") == resource_id:
            return True
        return False

    async def get_diff(self, db: AsyncSession, change_set_id: UUID) -> dict[str, Any]:
        """
        Returns what will change: added/removed/modified endpoints vs baseline.
        """
        change_set = await db.get(ChangeSet, change_set_id)
        if not change_set:
            raise ValueError(f"Change set {change_set_id} not found")

        changes = await self._get_changes(db, change_set_id)

        added = []
        removed = []
        modified = []

        for change in changes:
            resource = await db.get(DiscoveredResource, change.resource_id)
            resource_info = {
                "resource_id": str(change.resource_id),
                "resource_type": resource.type if resource else "unknown",
                "resource_source": resource.source if resource else "unknown",
                "resource_name": (
                    resource.resource_metadata.get("name", resource.source_id)
                    if resource else "unknown"
                ),
            }

            if change.change_type == "add":
                added.append({
                    "change_id": str(change.id),
                    **resource_info,
                    "settings": change.settings_after,
                })
            elif change.change_type == "remove":
                removed.append({
                    "change_id": str(change.id),
                    "exposure_id": str(change.exposure_id) if change.exposure_id else None,
                    **resource_info,
                    "settings": change.settings_before,
                })
            elif change.change_type == "modify":
                modified.append({
                    "change_id": str(change.id),
                    "exposure_id": str(change.exposure_id) if change.exposure_id else None,
                    **resource_info,
                    "settings_before": change.settings_before,
                    "settings_after": change.settings_after,
                })

        return {
            "change_set_id": str(change_set_id),
            "added": added,
            "removed": removed,
            "modified": modified,
            "total_changes": len(added) + len(removed) + len(modified),
        }

    async def submit(self, db: AsyncSession, change_set_id: UUID, user: str) -> ConfigVersion:
        """
        Submit a change set for approval.

        Creates a ConfigVersion with status=pending_approval containing the
        effective config snapshot, and links it to this change set.
        """
        change_set = await self._get_draft_change_set(db, change_set_id)

        # Generate the effective config
        effective_config = await self.get_effective_config(db, change_set_id)

        # Get next version number
        engine = DeploymentEngine()
        next_version = await engine._get_next_version(db)

        # Create config version
        config_version = ConfigVersion(
            version=next_version,
            config_snapshot=effective_config,
            created_by=user,
            commit_message=change_set.description or f"Change set submitted by {user}",
            status="pending_approval",
        )
        db.add(config_version)
        await db.flush()

        # Update change set
        change_set.status = "submitted"
        change_set.submitted_at = datetime.utcnow()
        change_set.config_version_id = config_version.id

        # Update all changes to pending_approval
        changes = await self._get_changes(db, change_set_id)
        for change in changes:
            change.status = "pending_approval"
            change.submitted_for_approval_at = datetime.utcnow()

        # Audit
        db.add(EventLog(
            event_type="change_set_submitted",
            entity_type="change_set",
            entity_id=change_set_id,
            user_id=user,
            event_metadata={
                "config_version_id": str(config_version.id),
                "version": next_version,
                "changes_count": len(changes),
            },
        ))

        await db.commit()
        await db.refresh(config_version)

        await event_bus.publish(EventType.CHANGE_SET_SUBMITTED, {
            "change_set_id": str(change_set_id),
            "config_version_id": str(config_version.id),
            "version": next_version,
            "submitted_by": user,
        })

        return config_version

    async def cancel(self, db: AsyncSession, change_set_id: UUID, user: str) -> ChangeSet:
        """Cancel a change set."""
        change_set = await db.get(ChangeSet, change_set_id)
        if not change_set:
            raise ValueError(f"Change set {change_set_id} not found")
        if change_set.status not in ("draft", "submitted"):
            raise ValueError(f"Cannot cancel change set with status: {change_set.status}")

        change_set.status = "cancelled"

        # Cancel all changes
        changes = await self._get_changes(db, change_set_id)
        for change in changes:
            change.status = "cancelled"

        # Audit
        db.add(EventLog(
            event_type="change_set_cancelled",
            entity_type="change_set",
            entity_id=change_set_id,
            user_id=user,
            event_metadata={"changes_count": len(changes)},
        ))

        await db.commit()
        await db.refresh(change_set)

        await event_bus.publish(EventType.CHANGE_SET_CANCELLED, {
            "change_set_id": str(change_set_id),
            "cancelled_by": user,
        })

        return change_set

    # -------------------------------------------------------------------------
    # Config version approval / rejection / deployment
    # -------------------------------------------------------------------------

    async def approve_config_version(
        self, db: AsyncSession, version_id: UUID, user: str, comments: str | None = None
    ) -> ConfigVersion:
        """Approve a config version for deployment."""
        config_version = await db.get(ConfigVersion, version_id)
        if not config_version:
            raise ValueError(f"Config version {version_id} not found")
        if config_version.status != "pending_approval":
            raise ValueError(f"Cannot approve version with status: {config_version.status}")

        config_version.status = "approved"
        config_version.approved_by = user
        config_version.approved_at = datetime.utcnow()

        # If linked to a change set, update its status too
        cs_query = select(ChangeSet).where(ChangeSet.config_version_id == version_id)
        cs_result = await db.execute(cs_query)
        change_set = cs_result.scalar_one_or_none()
        if change_set:
            change_set.status = "approved"
            # Update all changes
            changes = await self._get_changes(db, change_set.id)
            for change in changes:
                change.status = "approved"
                change.approved_by = user
                change.approved_at = datetime.utcnow()

        # Audit
        db.add(EventLog(
            event_type="config_version_approved",
            entity_type="config_version",
            entity_id=version_id,
            user_id=user,
            event_metadata={
                "version": config_version.version,
                "comments": comments,
            },
        ))

        await db.commit()
        await db.refresh(config_version)

        await event_bus.publish(EventType.CONFIG_VERSION_APPROVED, {
            "config_version_id": str(version_id),
            "version": config_version.version,
            "approved_by": user,
        })

        return config_version

    async def reject_config_version(
        self, db: AsyncSession, version_id: UUID, user: str, reason: str
    ) -> ConfigVersion:
        """Reject a config version."""
        config_version = await db.get(ConfigVersion, version_id)
        if not config_version:
            raise ValueError(f"Config version {version_id} not found")
        if config_version.status != "pending_approval":
            raise ValueError(f"Cannot reject version with status: {config_version.status}")

        config_version.status = "rejected"
        config_version.rejected_by = user
        config_version.rejected_at = datetime.utcnow()
        config_version.rejection_reason = reason

        # If linked to a change set, update its status
        cs_query = select(ChangeSet).where(ChangeSet.config_version_id == version_id)
        cs_result = await db.execute(cs_query)
        change_set = cs_result.scalar_one_or_none()
        if change_set:
            change_set.status = "rejected"
            changes = await self._get_changes(db, change_set.id)
            for change in changes:
                change.status = "rejected"
                change.rejected_by = user
                change.rejected_at = datetime.utcnow()
                change.rejection_reason = reason

        # Audit
        db.add(EventLog(
            event_type="config_version_rejected",
            entity_type="config_version",
            entity_id=version_id,
            user_id=user,
            event_metadata={
                "version": config_version.version,
                "reason": reason,
            },
        ))

        await db.commit()
        await db.refresh(config_version)

        await event_bus.publish(EventType.CONFIG_VERSION_REJECTED, {
            "config_version_id": str(version_id),
            "version": config_version.version,
            "rejected_by": user,
            "reason": reason,
        })

        return config_version

    async def deploy_config_version(
        self, db: AsyncSession, version_id: UUID, user: str
    ) -> tuple[bool, str, str | None]:
        """
        Deploy an approved config version to the gateway.

        Returns: (success, message, deployment_id)
        """
        config_version = await db.get(ConfigVersion, version_id)
        if not config_version:
            raise ValueError(f"Config version {version_id} not found")
        if config_version.status != "approved":
            raise ValueError(f"Cannot deploy version with status: {config_version.status}")

        engine = DeploymentEngine()

        # Import here to avoid circular reference
        from app.modules.gateway.models import Deployment

        # Create deployment record
        deployment = Deployment(
            version_id=version_id,
            status="in_progress",
            deployed_by=user,
        )
        db.add(deployment)
        await db.commit()
        await db.refresh(deployment)
        deployment_id = str(deployment.id)

        try:
            # Push config to gateway
            config = config_version.config_snapshot
            await engine._backend.update_config(config, config_version.version)

            # Rolling restart if applicable
            if hasattr(engine._backend, 'rolling_restart'):
                await engine._backend.rolling_restart()

            # Wait for ready
            if hasattr(engine._backend, 'wait_for_rollout'):
                if not await engine._backend.wait_for_rollout():
                    deployment.status = "failed"
                    deployment.error_message = "Rollout timeout"
                    await db.commit()
                    return (False, "Rollout timeout", deployment_id)
            elif hasattr(engine._backend, 'wait_for_ready'):
                if not await engine._backend.wait_for_ready():
                    deployment.status = "failed"
                    deployment.error_message = "KrakenD not ready"
                    await db.commit()
                    return (False, "KrakenD not ready", deployment_id)

            # Health check
            if not await engine._backend.health_check():
                deployment.status = "failed"
                deployment.error_message = "Health check failed"
                deployment.health_check_passed = False
                await db.commit()
                return (False, "Health check failed", deployment_id)

            # Success
            deployment.status = "succeeded"
            deployment.health_check_passed = True
            deployment.completed_at = datetime.utcnow()

            # Deactivate old versions
            old_query = select(ConfigVersion).where(ConfigVersion.is_active == True)
            old_result = await db.execute(old_query)
            for old in old_result.scalars().all():
                old.is_active = False

            config_version.is_active = True
            config_version.status = "deployed"
            config_version.deployed_to_gateway_at = datetime.utcnow()

            # Update linked change set and sync exposures table
            cs_query = select(ChangeSet).where(ChangeSet.config_version_id == version_id)
            cs_result = await db.execute(cs_query)
            change_set = cs_result.scalar_one_or_none()
            if change_set:
                change_set.status = "deployed"
                changes = await self._get_changes(db, change_set.id)
                for change in changes:
                    change.status = "deployed"
                    change.deployed_in_version_id = version_id
                    change.deployed_at = datetime.utcnow()

                    # Sync exposures table so it matches the deployed config
                    if change.change_type == "add":
                        resource = await db.get(DiscoveredResource, change.resource_id)
                        if resource:
                            try:
                                endpoint_config = self.generator_registry.generate_config(
                                    resource_id=str(resource.id),
                                    resource_type=resource.type,
                                    resource_metadata=resource.resource_metadata,
                                    settings=change.settings_after or {},
                                )
                                generated = endpoint_config.model_dump(exclude_none=True)
                                new_exposure = Exposure(
                                    resource_id=change.resource_id,
                                    settings=change.settings_after or {},
                                    generated_config=generated,
                                    status="deployed",
                                    created_by=user,
                                    deployed_in_version_id=version_id,
                                )
                                db.add(new_exposure)
                            except Exception:
                                pass  # Non-fatal: config is already deployed

                    elif change.change_type == "remove" and change.exposure_id:
                        exposure = await db.get(Exposure, change.exposure_id)
                        if exposure:
                            exposure.status = "removed"
                            exposure.removed_in_version_id = version_id

                    elif change.change_type == "modify" and change.exposure_id:
                        exposure = await db.get(Exposure, change.exposure_id)
                        if exposure:
                            exposure.settings = change.settings_after or exposure.settings
                            try:
                                resource = await db.get(DiscoveredResource, exposure.resource_id)
                                if resource:
                                    endpoint_config = self.generator_registry.generate_config(
                                        resource_id=str(resource.id),
                                        resource_type=resource.type,
                                        resource_metadata=resource.resource_metadata,
                                        settings=change.settings_after or {},
                                    )
                                    exposure.generated_config = endpoint_config.model_dump(exclude_none=True)
                            except Exception:
                                pass  # Non-fatal

            # Audit
            db.add(EventLog(
                event_type="config_version_deployed",
                entity_type="config_version",
                entity_id=version_id,
                user_id=user,
                event_metadata={
                    "version": config_version.version,
                    "deployment_id": deployment_id,
                },
            ))

            await db.commit()

            await event_bus.publish(EventType.CONFIG_VERSION_DEPLOYED, {
                "config_version_id": str(version_id),
                "version": config_version.version,
                "deployment_id": deployment_id,
                "deployed_by": user,
            })

            return (True, f"Successfully deployed version {config_version.version}", deployment_id)

        except Exception as e:
            deployment.status = "failed"
            deployment.error_message = str(e)
            await db.commit()
            return (False, f"Deployment failed: {str(e)}", deployment_id)

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    async def _get_draft_change_set(self, db: AsyncSession, change_set_id: UUID) -> ChangeSet:
        """Get a change set and verify it's still in draft status."""
        change_set = await db.get(ChangeSet, change_set_id)
        if not change_set:
            raise ValueError(f"Change set {change_set_id} not found")
        if change_set.status != "draft":
            raise ValueError(f"Change set is not in draft status (current: {change_set.status})")
        return change_set

    async def _get_changes(self, db: AsyncSession, change_set_id: UUID) -> list[ExposureChange]:
        """Get all changes in a change set."""
        query = select(ExposureChange).where(ExposureChange.change_set_id == change_set_id)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def _find_change(
        self, db: AsyncSession, change_set_id: UUID, change_type: str,
        resource_id: UUID | None = None
    ) -> ExposureChange | None:
        """Find an existing change in a change set by type and resource_id."""
        query = (
            select(ExposureChange)
            .where(ExposureChange.change_set_id == change_set_id)
            .where(ExposureChange.change_type == change_type)
        )
        if resource_id:
            query = query.where(ExposureChange.resource_id == resource_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()


# Singleton
change_set_service = ChangeSetService()
