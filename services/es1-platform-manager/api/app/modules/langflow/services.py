"""Langflow discovery and sync services."""
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.events import event_bus, EventType
from app.modules.gateway.models import DiscoveredResource
from .client import langflow_client

logger = get_logger(__name__)


class LangflowDiscoveryService:
    """
    Service for discovering and syncing Langflow resources.

    Discovers:
    - Flows as flow resources
    """

    def __init__(self):
        """Initialize discovery service."""
        self.client = langflow_client

    async def discover_flows(self, db: AsyncSession) -> list[DiscoveredResource]:
        """
        Discover flows from Langflow and sync to database.

        Args:
            db: Database session

        Returns:
            List of discovered/updated resources
        """
        discovered = []

        if not self.client.enabled:
            logger.info("Langflow integration is disabled, skipping discovery")
            return discovered

        try:
            # Get all flows from Langflow
            flows = await self.client.list_flows()

            logger.info(f"Discovered {len(flows)} flows from Langflow")

            for flow in flows:
                flow_id = flow.get("id")
                if not flow_id:
                    continue

                # Check if resource already exists
                query = select(DiscoveredResource).where(
                    DiscoveredResource.source == "langflow",
                    DiscoveredResource.source_id == flow_id,
                    DiscoveredResource.type == "flow",
                )
                result = await db.execute(query)
                existing = result.scalar_one_or_none()

                # Build metadata
                metadata = {
                    "flow_id": flow_id,
                    "name": flow.get("name", flow_id),
                    "description": flow.get("description"),
                    "endpoint_name": flow.get("endpoint_name"),
                    "is_component": flow.get("is_component", False),
                    "updated_at": flow.get("updated_at"),
                    "folder_id": flow.get("folder_id"),
                    "user_id": flow.get("user_id"),
                }

                if existing:
                    # Update existing resource
                    existing.resource_metadata = metadata
                    existing.last_updated = datetime.utcnow()
                    discovered.append(existing)
                else:
                    # Create new resource
                    resource = DiscoveredResource(
                        type="flow",
                        source="langflow",
                        source_id=flow_id,
                        resource_metadata=metadata,
                        status="active",
                    )
                    db.add(resource)
                    discovered.append(resource)

                    # Emit event for new resource
                    await event_bus.publish(
                        EventType.RESOURCE_DISCOVERED,
                        {
                            "type": "flow",
                            "source": "langflow",
                            "source_id": flow_id,
                            "name": metadata["name"],
                        },
                    )

            await db.commit()
            logger.info(f"Synced {len(discovered)} flow resources")

        except Exception as e:
            logger.error(f"Failed to discover flows: {e}")
            raise

        return discovered

    async def discover_all(self, db: AsyncSession) -> dict[str, list[DiscoveredResource]]:
        """
        Discover all resources from Langflow.

        Args:
            db: Database session

        Returns:
            Dict with 'flows' list
        """
        flows = await self.discover_flows(db)

        return {
            "flows": flows,
        }


# Singleton instance
langflow_discovery = LangflowDiscoveryService()
