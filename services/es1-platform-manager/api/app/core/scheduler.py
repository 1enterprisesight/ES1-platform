"""Background scheduler for periodic resource discovery."""
import asyncio
from datetime import datetime
from typing import Callable, Any

from app.core.config import settings
from app.core.logging import get_logger
from app.core.events import event_bus, EventType

logger = get_logger(__name__)


class DiscoveryScheduler:
    """
    Background scheduler for periodic resource discovery.

    Runs discovery tasks at configurable intervals to keep
    the platform's view of external resources up to date.
    """

    def __init__(self):
        """Initialize the scheduler."""
        self._running = False
        self._tasks: list[asyncio.Task] = []
        self._discovery_interval = settings.DISCOVERY_INTERVAL_SECONDS
        self._last_discovery: dict[str, datetime | None] = {
            "airflow": None,
            "langflow": None,
            "gateway": None,
        }

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running

    @property
    def last_discovery(self) -> dict[str, datetime | None]:
        """Get last discovery times for each service."""
        return self._last_discovery.copy()

    async def start(self):
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        logger.info(
            "Starting discovery scheduler",
            interval_seconds=self._discovery_interval,
        )

        # Start the main discovery loop
        task = asyncio.create_task(self._discovery_loop())
        self._tasks.append(task)

        await event_bus.publish(
            EventType.SYSTEM_INFO,
            {
                "message": "Discovery scheduler started",
                "interval_seconds": self._discovery_interval,
            },
        )

    async def stop(self):
        """Stop the scheduler."""
        if not self._running:
            return

        self._running = False
        logger.info("Stopping discovery scheduler...")

        # Cancel all running tasks
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._tasks.clear()

        await event_bus.publish(
            EventType.SYSTEM_INFO,
            {"message": "Discovery scheduler stopped"},
        )

    async def run_discovery_now(self, services: list[str] | None = None):
        """
        Run discovery immediately for specified services.

        Args:
            services: List of services to discover. If None, discover all.
        """
        if services is None:
            services = ["airflow", "langflow", "gateway"]

        logger.info("Running immediate discovery", services=services)

        await event_bus.publish(
            EventType.OPERATION_STARTED,
            {
                "operation": "manual_discovery",
                "services": services,
                "message": f"Starting discovery for: {', '.join(services)}",
            },
        )

        results = {}
        for service in services:
            try:
                result = await self._discover_service(service)
                results[service] = {"status": "success", "data": result}
                self._last_discovery[service] = datetime.utcnow()
            except Exception as e:
                logger.error(f"Discovery failed for {service}: {e}")
                results[service] = {"status": "error", "error": str(e)}

        await event_bus.publish(
            EventType.OPERATION_COMPLETED,
            {
                "operation": "manual_discovery",
                "services": services,
                "results": results,
                "message": "Discovery completed",
            },
        )

        return results

    async def _discovery_loop(self):
        """Main discovery loop that runs periodically."""
        while self._running:
            try:
                await self._run_scheduled_discovery()
            except Exception as e:
                logger.error(f"Scheduled discovery error: {e}")
                await event_bus.publish(
                    EventType.SYSTEM_ERROR,
                    {
                        "error": str(e),
                        "context": "scheduled_discovery",
                    },
                )

            # Wait for next interval
            await asyncio.sleep(self._discovery_interval)

    async def _run_scheduled_discovery(self):
        """Run scheduled discovery for all services."""
        logger.info("Running scheduled discovery...")

        await event_bus.publish(
            EventType.OPERATION_STARTED,
            {
                "operation": "scheduled_discovery",
                "message": "Starting scheduled resource discovery",
            },
        )

        services = ["airflow", "langflow"]
        total_discovered = 0

        for service in services:
            try:
                result = await self._discover_service(service)
                self._last_discovery[service] = datetime.utcnow()

                count = result.get("count", 0)
                total_discovered += count

                logger.info(
                    f"Discovered {count} resources from {service}",
                    service=service,
                    count=count,
                )
            except Exception as e:
                logger.warning(f"Failed to discover from {service}: {e}")

        await event_bus.publish(
            EventType.OPERATION_COMPLETED,
            {
                "operation": "scheduled_discovery",
                "total_discovered": total_discovered,
                "message": f"Scheduled discovery completed: {total_discovered} resources",
            },
        )

    async def _discover_service(self, service: str) -> dict[str, Any]:
        """
        Discover resources from a specific service.

        Args:
            service: Service name (airflow, langflow, gateway)

        Returns:
            Discovery result dict
        """
        if service == "airflow":
            return await self._discover_airflow()
        elif service == "langflow":
            return await self._discover_langflow()
        elif service == "gateway":
            return await self._discover_gateway()
        else:
            raise ValueError(f"Unknown service: {service}")

    async def _discover_airflow(self) -> dict[str, Any]:
        """Discover resources from Airflow."""
        from app.modules.airflow.client import airflow_client

        if not settings.AIRFLOW_ENABLED:
            return {"count": 0, "message": "Airflow integration disabled"}

        try:
            health = await airflow_client.health_check()
            if health.get("status") != "healthy":
                return {"count": 0, "message": "Airflow not healthy"}

            dags = await airflow_client.list_dags()
            dag_list = dags.get("dags", [])

            return {
                "count": len(dag_list),
                "dags": [d.get("dag_id") for d in dag_list[:10]],  # First 10
                "message": f"Discovered {len(dag_list)} DAGs",
            }
        except Exception as e:
            logger.error(f"Airflow discovery error: {e}")
            raise

    async def _discover_langflow(self) -> dict[str, Any]:
        """Discover resources from Langflow."""
        from app.modules.langflow.client import langflow_client

        if not settings.LANGFLOW_ENABLED:
            return {"count": 0, "message": "Langflow integration disabled"}

        try:
            health = await langflow_client.health_check()
            if health.get("status") != "healthy":
                return {"count": 0, "message": "Langflow not healthy"}

            flows = await langflow_client.list_flows()

            return {
                "count": len(flows),
                "flows": [f.get("name") for f in flows[:10]],  # First 10
                "message": f"Discovered {len(flows)} flows",
            }
        except Exception as e:
            logger.error(f"Langflow discovery error: {e}")
            raise

    async def _discover_gateway(self) -> dict[str, Any]:
        """Discover resources for gateway exposure."""
        from app.core.database import async_session_factory
        from app.modules.gateway.models import DiscoveredResource
        from sqlalchemy import select, func

        async with async_session_factory() as session:
            count = await session.scalar(
                select(func.count()).select_from(DiscoveredResource)
            )

        return {
            "count": count or 0,
            "message": f"Found {count or 0} discovered resources",
        }


# Singleton instance
discovery_scheduler = DiscoveryScheduler()
