"""
KrakenD Config Validator

Validates KrakenD configuration files. In Kubernetes environments, uses temporary
K8s Jobs to run krakend check. In local/Docker environments, performs basic
JSON schema validation.
"""

import asyncio
import json
import os
import time
from typing import Tuple, Optional

# Kubernetes client is optional - only used when running in K8s
try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    K8S_AVAILABLE = True
except ImportError:
    K8S_AVAILABLE = False
    ApiException = Exception


class KrakenDConfigValidator:
    """Validates KrakenD configs using temporary Kubernetes Job or local validation"""

    def __init__(self, namespace: str = "es1-platform"):
        """
        Initialize validator

        Args:
            namespace: Kubernetes namespace for validation jobs
        """
        self.namespace = namespace
        self.k8s_enabled = False
        self.batch_v1 = None
        self.core_v1 = None
        self.krakend_image = "devopsfaith/krakend:2.6"

        # Only try to connect to Kubernetes if available and not explicitly disabled
        if K8S_AVAILABLE and os.environ.get("DISABLE_K8S_VALIDATION", "").lower() != "true":
            try:
                config.load_incluster_config()
                self._init_k8s_clients()
                self.k8s_enabled = True
            except config.ConfigException:
                try:
                    config.load_kube_config()
                    self._init_k8s_clients()
                    self.k8s_enabled = True
                except Exception:
                    # No Kubernetes config available, use local validation
                    pass

    def _init_k8s_clients(self):
        """Initialize Kubernetes API clients"""
        self.batch_v1 = client.BatchV1Api()
        self.core_v1 = client.CoreV1Api()

    async def validate_config(self, config_dict: dict) -> Tuple[bool, str]:
        """
        Validates KrakenD config

        In Kubernetes: spins up temp K8s Job with krakend check
        Locally: performs basic JSON structure validation

        Args:
            config_dict: KrakenD configuration dictionary

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if config is valid, False otherwise
            - error_message: Empty string if valid, error details if invalid
        """
        if self.k8s_enabled:
            return await self._validate_with_k8s(config_dict)
        else:
            return self._validate_locally(config_dict)

    def _validate_locally(self, config_dict: dict) -> Tuple[bool, str]:
        """
        Perform local validation of KrakenD config structure

        This is a basic validation that checks:
        - Required fields exist
        - Endpoints are properly structured
        - Backend definitions are valid
        """
        errors = []

        # Check version
        if "version" not in config_dict:
            errors.append("Missing required field: version")
        elif config_dict["version"] not in [2, 3]:
            errors.append(f"Invalid version: {config_dict['version']}. Must be 2 or 3")

        # Check endpoints exist
        if "endpoints" not in config_dict:
            errors.append("Missing required field: endpoints")
        elif not isinstance(config_dict["endpoints"], list):
            errors.append("Field 'endpoints' must be an array")
        else:
            # Validate each endpoint
            for i, endpoint in enumerate(config_dict["endpoints"]):
                endpoint_errors = self._validate_endpoint(endpoint, i)
                errors.extend(endpoint_errors)

        if errors:
            return (False, "; ".join(errors))
        return (True, "")

    def _validate_endpoint(self, endpoint: dict, index: int) -> list:
        """Validate a single endpoint configuration"""
        errors = []
        prefix = f"endpoints[{index}]"

        if not isinstance(endpoint, dict):
            return [f"{prefix}: must be an object"]

        # Required fields
        if "endpoint" not in endpoint:
            errors.append(f"{prefix}: missing required field 'endpoint'")
        elif not endpoint["endpoint"].startswith("/"):
            errors.append(f"{prefix}: endpoint path must start with '/'")

        if "backend" not in endpoint:
            errors.append(f"{prefix}: missing required field 'backend'")
        elif not isinstance(endpoint["backend"], list):
            errors.append(f"{prefix}: 'backend' must be an array")
        elif len(endpoint["backend"]) == 0:
            errors.append(f"{prefix}: 'backend' array cannot be empty")
        else:
            # Validate backends
            for j, backend in enumerate(endpoint["backend"]):
                backend_errors = self._validate_backend(backend, f"{prefix}.backend[{j}]")
                errors.extend(backend_errors)

        return errors

    def _validate_backend(self, backend: dict, prefix: str) -> list:
        """Validate a single backend configuration"""
        errors = []

        if not isinstance(backend, dict):
            return [f"{prefix}: must be an object"]

        # Check for static response (no host/url_pattern needed)
        extra_config = backend.get("extra_config", {})
        if "proxy" in extra_config and "static" in extra_config.get("proxy", {}):
            return []  # Static response, no backend validation needed

        # For non-static backends, host is required
        if "host" not in backend:
            errors.append(f"{prefix}: missing required field 'host'")
        elif not isinstance(backend["host"], list):
            errors.append(f"{prefix}: 'host' must be an array")
        elif len(backend["host"]) == 0:
            errors.append(f"{prefix}: 'host' array cannot be empty")

        if "url_pattern" not in backend:
            errors.append(f"{prefix}: missing required field 'url_pattern'")

        return errors

    async def _validate_with_k8s(self, config_dict: dict) -> Tuple[bool, str]:
        """
        Validates KrakenD config by spinning up temp K8s Job

        Args:
            config_dict: KrakenD configuration dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        timestamp = int(time.time())
        job_name = f"krakend-validate-{timestamp}"
        configmap_name = f"{job_name}-config"

        try:
            # 1. Create ConfigMap with draft config
            await self._create_config_map(configmap_name, config_dict)

            # 2. Create Job that runs krakend check
            await self._create_validation_job(job_name, configmap_name)

            # 3. Wait for Job completion (timeout 30s)
            success = await self._wait_for_job(job_name, timeout=30)

            # 4. Get Job logs for validation result
            logs = await self._get_job_logs(job_name)

            # 5. Parse result
            if success and ("Syntax OK" in logs or "valid" in logs.lower()):
                return (True, "")
            else:
                return (False, logs if logs else "Validation failed with no output")

        except Exception as e:
            return (False, f"Validation error: {str(e)}")

        finally:
            # 6. Cleanup
            await self._cleanup(job_name, configmap_name)

    async def _create_config_map(self, name: str, config_dict: dict):
        """Create ConfigMap with config JSON"""
        config_map = client.V1ConfigMap(
            metadata=client.V1ObjectMeta(
                name=name,
                namespace=self.namespace,
                labels={"app": "es1-gateway-manager", "component": "config-validator"}
            ),
            data={
                "krakend.json": json.dumps(config_dict, indent=2)
            }
        )

        try:
            await asyncio.to_thread(
                self.core_v1.create_namespaced_config_map,
                namespace=self.namespace,
                body=config_map
            )
        except ApiException as e:
            raise Exception(f"Failed to create ConfigMap: {e.reason}")

    async def _create_validation_job(self, job_name: str, configmap_name: str):
        """Create Job with krakend image to validate config"""
        job = client.V1Job(
            metadata=client.V1ObjectMeta(
                name=job_name,
                namespace=self.namespace,
                labels={"app": "es1-gateway-manager", "component": "config-validator"}
            ),
            spec=client.V1JobSpec(
                ttl_seconds_after_finished=60,
                backoff_limit=0,
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        labels={"app": "es1-gateway-manager", "job": job_name}
                    ),
                    spec=client.V1PodSpec(
                        restart_policy="Never",
                        containers=[
                            client.V1Container(
                                name="validator",
                                image=self.krakend_image,
                                command=["krakend"],
                                args=["check", "-c", "/config/krakend.json"],
                                volume_mounts=[
                                    client.V1VolumeMount(
                                        name="config",
                                        mount_path="/config"
                                    )
                                ],
                                resources=client.V1ResourceRequirements(
                                    requests={"cpu": "100m", "memory": "128Mi"},
                                    limits={"cpu": "200m", "memory": "256Mi"}
                                )
                            )
                        ],
                        volumes=[
                            client.V1Volume(
                                name="config",
                                config_map=client.V1ConfigMapVolumeSource(
                                    name=configmap_name
                                )
                            )
                        ]
                    )
                )
            )
        )

        try:
            await asyncio.to_thread(
                self.batch_v1.create_namespaced_job,
                namespace=self.namespace,
                body=job
            )
        except ApiException as e:
            raise Exception(f"Failed to create validation Job: {e.reason}")

    async def _wait_for_job(self, job_name: str, timeout: int) -> bool:
        """Poll Job status until Complete or Failed"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                job = await asyncio.to_thread(
                    self.batch_v1.read_namespaced_job_status,
                    name=job_name,
                    namespace=self.namespace
                )

                if job.status.succeeded:
                    return True
                if job.status.failed:
                    return False

                await asyncio.sleep(1)

            except ApiException as e:
                raise Exception(f"Failed to read Job status: {e.reason}")

        return False

    async def _get_job_logs(self, job_name: str) -> str:
        """Get logs from Job pod"""
        try:
            pods = await asyncio.to_thread(
                self.core_v1.list_namespaced_pod,
                namespace=self.namespace,
                label_selector=f"job-name={job_name}"
            )

            if not pods.items:
                return "No pod found for validation job"

            pod_name = pods.items[0].metadata.name

            logs = await asyncio.to_thread(
                self.core_v1.read_namespaced_pod_log,
                name=pod_name,
                namespace=self.namespace
            )

            return logs

        except ApiException as e:
            return f"Failed to read logs: {e.reason}"

    async def _cleanup(self, job_name: str, configmap_name: str):
        """Delete Job and ConfigMap"""
        try:
            await asyncio.to_thread(
                self.batch_v1.delete_namespaced_job,
                name=job_name,
                namespace=self.namespace,
                propagation_policy='Background'
            )
        except ApiException:
            pass

        try:
            await asyncio.to_thread(
                self.core_v1.delete_namespaced_config_map,
                name=configmap_name,
                namespace=self.namespace
            )
        except ApiException:
            pass


# Singleton validator instance - lazy initialized
_validator: Optional[KrakenDConfigValidator] = None


def get_validator() -> KrakenDConfigValidator:
    """Get or create the singleton validator instance"""
    global _validator
    if _validator is None:
        _validator = KrakenDConfigValidator()
    return _validator
