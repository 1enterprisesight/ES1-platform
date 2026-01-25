"""Docker-specific deployment engine for local development."""
import json
import httpx
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Any

from app.core.config import settings


class DockerDeploymentEngine:
    """
    Deployment engine for Docker Compose environment.

    Uses HTTP-based health checks and file-based config deployment
    instead of Kubernetes API.
    """

    def __init__(self):
        """Initialize Docker deployment engine."""
        self.krakend_url = settings.KRAKEND_URL
        self.krakend_health_url = settings.KRAKEND_HEALTH_URL
        self.krakend_metrics_url = settings.KRAKEND_METRICS_URL
        self.config_path = Path(settings.KRAKEND_CONFIG_PATH)

    async def get_health_details(self) -> dict[str, Any]:
        """
        Get KrakenD health status via HTTP.

        In Docker mode, we check health via HTTP endpoint instead of
        Kubernetes pod status.

        Returns:
            dict: Health status with status, pod_count (always 1 in Docker),
                  running_pods, and failed_health_checks
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.krakend_health_url)

                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "pod_count": 1,  # Docker = single container
                        "running_pods": 1,
                        "failed_health_checks": 0,
                        "mode": "docker",
                    }
                else:
                    return {
                        "status": "degraded",
                        "pod_count": 1,
                        "running_pods": 0,
                        "failed_health_checks": 1,
                        "mode": "docker",
                        "http_status": response.status_code,
                    }

        except httpx.ConnectError:
            return {
                "status": "unhealthy",
                "pod_count": 1,
                "running_pods": 0,
                "failed_health_checks": 1,
                "mode": "docker",
                "error": "Connection refused - KrakenD container not running",
            }
        except httpx.TimeoutException:
            return {
                "status": "unhealthy",
                "pod_count": 1,
                "running_pods": 0,
                "failed_health_checks": 1,
                "mode": "docker",
                "error": "Health check timeout",
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "pod_count": 0,
                "running_pods": 0,
                "failed_health_checks": 1,
                "mode": "docker",
                "error": str(e),
            }

    async def health_check(self) -> bool:
        """
        Check if KrakenD is healthy.

        Returns:
            bool: True if healthy, False otherwise
        """
        health = await self.get_health_details()
        return health["status"] == "healthy"

    async def update_config(self, config: dict[str, Any], version: int) -> str:
        """
        Deploy config by writing to shared volume.

        In Docker mode, we write the config to a shared volume that
        KrakenD mounts. KrakenD can be configured to watch for file
        changes or we can signal it to reload.

        Args:
            config: The complete KrakenD configuration
            version: The configuration version number

        Returns:
            str: Identifier for this config deployment
        """
        # Ensure parent directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Write config with pretty formatting
        config_json = json.dumps(config, indent=2)
        self.config_path.write_text(config_json)

        # Also write a versioned backup
        backup_path = self.config_path.parent / f"krakend.v{version}.json"
        backup_path.write_text(config_json)

        return f"docker-config-v{version}"

    async def trigger_reload(self) -> bool:
        """
        Trigger KrakenD to reload configuration.

        For now, we rely on file watcher or container restart.

        Returns:
            bool: True (we assume file-based reload works)
        """
        return True

    async def wait_for_ready(self, timeout: int = 30) -> bool:
        """
        Wait for KrakenD to become ready after config change.

        Args:
            timeout: Maximum seconds to wait

        Returns:
            bool: True if ready within timeout, False otherwise
        """
        start_time = datetime.utcnow()

        while True:
            if await self.health_check():
                return True

            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed > timeout:
                return False

            await asyncio.sleep(1)

    async def get_current_config(self) -> dict[str, Any] | None:
        """
        Get the currently deployed configuration.

        Returns:
            dict: Current config if file exists, None otherwise
        """
        if self.config_path.exists():
            try:
                config_text = self.config_path.read_text()
                return json.loads(config_text)
            except (json.JSONDecodeError, IOError):
                return None
        return None

    async def list_config_versions(self) -> list[dict[str, Any]]:
        """
        List available configuration versions from backup files.

        Returns:
            list: List of version info dicts
        """
        versions = []
        config_dir = self.config_path.parent

        if config_dir.exists():
            for file_path in config_dir.glob("krakend.v*.json"):
                try:
                    # Extract version number from filename
                    version_str = file_path.stem.replace("krakend.v", "")
                    version_num = int(version_str)

                    # Get file modification time
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

                    versions.append({
                        "version": version_num,
                        "file": str(file_path),
                        "modified_at": mtime.isoformat(),
                    })
                except (ValueError, OSError):
                    continue

        # Sort by version descending
        versions.sort(key=lambda v: v["version"], reverse=True)
        return versions

    async def rollback_to_version(self, version: int) -> bool:
        """
        Rollback to a previous configuration version.

        Args:
            version: Version number to rollback to

        Returns:
            bool: True if rollback successful, False otherwise
        """
        backup_path = self.config_path.parent / f"krakend.v{version}.json"

        if not backup_path.exists():
            return False

        try:
            # Read backup config
            backup_config = backup_path.read_text()

            # Write to main config file
            self.config_path.write_text(backup_config)

            # Trigger reload
            return await self.trigger_reload()
        except IOError:
            return False
