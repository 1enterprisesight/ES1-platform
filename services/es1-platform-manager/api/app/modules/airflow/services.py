"""Airflow discovery and sync services."""
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.events import event_bus, EventType
from app.modules.gateway.models import DiscoveredResource
from .client import airflow_client

logger = get_logger(__name__)


class AirflowDiscoveryService:
    """
    Service for discovering and syncing Airflow resources.

    Discovers:
    - DAGs as workflow resources
    - Connections as connection resources
    """

    def __init__(self):
        """Initialize discovery service."""
        self.client = airflow_client

    async def discover_dags(self, db: AsyncSession) -> list[DiscoveredResource]:
        """
        Discover DAGs from Airflow and sync to database.

        Adds/updates resources for DAGs that exist in Airflow,
        and marks resources as deleted when DAGs are removed.

        Args:
            db: Database session

        Returns:
            List of discovered/updated resources
        """
        discovered = []

        try:
            # Get all DAGs from Airflow (including paused/inactive)
            result = await self.client.list_dags(limit=1000, only_active=False)
            dags = result.get("dags", [])

            logger.info(f"Discovered {len(dags)} DAGs from Airflow")

            seen_dag_ids = set()

            for dag in dags:
                dag_id = dag.get("dag_id")
                if not dag_id:
                    continue

                seen_dag_ids.add(dag_id)

                # Check if resource already exists
                query = select(DiscoveredResource).where(
                    DiscoveredResource.source == "airflow",
                    DiscoveredResource.source_id == dag_id,
                    DiscoveredResource.type == "workflow",
                )
                result = await db.execute(query)
                existing = result.scalar_one_or_none()

                # Build metadata
                metadata = {
                    "dag_id": dag_id,
                    "name": dag.get("dag_display_name") or dag_id,
                    "description": dag.get("description"),
                    "file_token": dag.get("file_token"),
                    "is_paused": dag.get("is_paused", False),
                    "is_active": dag.get("is_active", True),
                    "schedule_interval": dag.get("schedule_interval"),
                    "timetable_description": dag.get("timetable_description"),
                    "tags": [t.get("name") for t in dag.get("tags", [])],
                    "owners": dag.get("owners", []),
                    "last_parsed_time": dag.get("last_parsed_time"),
                    "next_dagrun": dag.get("next_dagrun"),
                }

                if existing:
                    # Update existing resource
                    existing.resource_metadata = metadata
                    existing.last_updated = datetime.utcnow()
                    existing.status = "active"
                    discovered.append(existing)
                else:
                    # Create new resource
                    resource = DiscoveredResource(
                        type="workflow",
                        source="airflow",
                        source_id=dag_id,
                        resource_metadata=metadata,
                        status="active",
                    )
                    db.add(resource)
                    discovered.append(resource)

                    # Emit event for new resource
                    await event_bus.publish(
                        EventType.RESOURCE_DISCOVERED,
                        {
                            "type": "workflow",
                            "source": "airflow",
                            "source_id": dag_id,
                            "name": metadata["name"],
                        },
                    )

            # Mark stale resources as deleted (exist in DB but not in Airflow)
            stale_query = select(DiscoveredResource).where(
                DiscoveredResource.source == "airflow",
                DiscoveredResource.type == "workflow",
                DiscoveredResource.status != "deleted",
            )
            stale_result = await db.execute(stale_query)
            stale_count = 0
            for resource in stale_result.scalars().all():
                if resource.source_id not in seen_dag_ids:
                    resource.status = "deleted"
                    resource.last_updated = datetime.utcnow()
                    stale_count += 1
                    await event_bus.publish(
                        EventType.RESOURCE_DELETED,
                        {"resource_id": str(resource.id), "source_id": resource.source_id},
                    )

            await db.commit()
            logger.info(f"Synced {len(discovered)} DAG resources, marked {stale_count} as deleted")

        except Exception as e:
            logger.error(f"Failed to discover DAGs: {e}")
            raise

        return discovered

    async def discover_connections(self, db: AsyncSession) -> list[DiscoveredResource]:
        """
        Discover connections from Airflow and sync to database.

        Adds/updates resources for connections that exist in Airflow,
        and marks resources as deleted when connections are removed.

        Args:
            db: Database session

        Returns:
            List of discovered/updated resources
        """
        discovered = []

        try:
            # Get all connections from Airflow
            result = await self.client.get_connections(limit=1000)
            connections = result.get("connections", [])

            logger.info(f"Discovered {len(connections)} connections from Airflow")

            seen_conn_ids = set()

            for conn in connections:
                conn_id = conn.get("connection_id")
                if not conn_id:
                    continue

                seen_conn_ids.add(conn_id)

                # Check if resource already exists
                query = select(DiscoveredResource).where(
                    DiscoveredResource.source == "airflow",
                    DiscoveredResource.source_id == conn_id,
                    DiscoveredResource.type == "connection",
                )
                result = await db.execute(query)
                existing = result.scalar_one_or_none()

                # Build metadata (exclude sensitive data)
                metadata = {
                    "conn_id": conn_id,
                    "name": conn_id,
                    "conn_type": conn.get("conn_type"),
                    "description": conn.get("description"),
                    "host": conn.get("host"),
                    "port": conn.get("port"),
                    "schema": conn.get("schema"),
                    # Note: password and extra are excluded for security
                }

                if existing:
                    existing.resource_metadata = metadata
                    existing.last_updated = datetime.utcnow()
                    existing.status = "active"
                    discovered.append(existing)
                else:
                    resource = DiscoveredResource(
                        type="connection",
                        source="airflow",
                        source_id=conn_id,
                        resource_metadata=metadata,
                        status="active",
                    )
                    db.add(resource)
                    discovered.append(resource)

                    await event_bus.publish(
                        EventType.RESOURCE_DISCOVERED,
                        {
                            "type": "connection",
                            "source": "airflow",
                            "source_id": conn_id,
                            "name": conn_id,
                        },
                    )

            # Mark stale connection resources as deleted
            stale_query = select(DiscoveredResource).where(
                DiscoveredResource.source == "airflow",
                DiscoveredResource.type == "connection",
                DiscoveredResource.status != "deleted",
            )
            stale_result = await db.execute(stale_query)
            stale_count = 0
            for resource in stale_result.scalars().all():
                if resource.source_id not in seen_conn_ids:
                    resource.status = "deleted"
                    resource.last_updated = datetime.utcnow()
                    stale_count += 1

            await db.commit()
            logger.info(f"Synced {len(discovered)} connection resources, marked {stale_count} as deleted")

        except Exception as e:
            logger.error(f"Failed to discover connections: {e}")
            raise

        return discovered

    async def discover_all(self, db: AsyncSession) -> dict[str, list[DiscoveredResource]]:
        """
        Discover all resources from Airflow.

        Args:
            db: Database session

        Returns:
            Dict with 'dags' and 'connections' lists
        """
        dags = await self.discover_dags(db)
        connections = await self.discover_connections(db)

        return {
            "dags": dags,
            "connections": connections,
        }


# Singleton instance
airflow_discovery = AirflowDiscoveryService()
