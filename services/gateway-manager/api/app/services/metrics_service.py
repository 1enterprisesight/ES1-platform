"""Service for fetching and parsing KrakenD metrics."""
import re
import requests
from typing import Dict, List, Optional

from app.core.config import settings


class MetricsService:
    """Service to fetch and parse KrakenD Prometheus metrics."""

    def __init__(self, krakend_metrics_url: str | None = None):
        """
        Initialize metrics service.

        Args:
            krakend_metrics_url: URL to KrakenD Prometheus metrics endpoint.
                                 Defaults to settings.KRAKEND_METRICS_URL
        """
        self.metrics_url = krakend_metrics_url or settings.KRAKEND_METRICS_URL

    def fetch_raw_metrics(self) -> str:
        """
        Fetch raw Prometheus metrics from KrakenD.

        Returns:
            Raw metrics text in Prometheus format

        Raises:
            Exception: If metrics cannot be fetched
        """
        try:
            response = requests.get(self.metrics_url, timeout=5)
            response.raise_for_status()
            return response.text
        except Exception as e:
            raise Exception(f"Failed to fetch KrakenD metrics: {str(e)}")

    def parse_metrics(self, metrics_text: str) -> List[Dict]:
        """
        Parse Prometheus format metrics text.

        Format:
            # HELP metric_name description
            # TYPE metric_name type
            metric_name{label1="value1",label2="value2"} value timestamp

        Args:
            metrics_text: Raw Prometheus metrics text

        Returns:
            List of parsed metric dicts with keys: name, labels, value
        """
        metrics = []
        lines = metrics_text.split('\n')

        for line in lines:
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            # Parse metric line: metric_name{labels} value
            # Example: krakend_router_requests_total{code="200",method="GET"} 42
            match = re.match(r'^([a-zA-Z_:][a-zA-Z0-9_:]*)\s+([\d.e+-]+)', line)
            if not match:
                # Try with labels
                match = re.match(
                    r'^([a-zA-Z_:][a-zA-Z0-9_:]*)\{([^}]+)\}\s+([\d.e+-]+)',
                    line
                )
                if match:
                    metric_name = match.group(1)
                    labels_str = match.group(2)
                    value = float(match.group(3))

                    # Parse labels
                    labels = {}
                    label_pairs = re.findall(r'(\w+)="([^"]*)"', labels_str)
                    for key, val in label_pairs:
                        labels[key] = val

                    metrics.append({
                        'name': metric_name,
                        'labels': labels,
                        'value': value
                    })
            else:
                # No labels
                metric_name = match.group(1)
                value = float(match.group(2))

                metrics.append({
                    'name': metric_name,
                    'labels': {},
                    'value': value
                })

        return metrics

    def get_metric_value(
        self,
        metrics: List[Dict],
        metric_name: str,
        labels: Optional[Dict[str, str]] = None
    ) -> Optional[float]:
        """
        Get value for a specific metric with optional label filtering.

        Args:
            metrics: List of parsed metrics
            metric_name: Name of metric to find
            labels: Optional dict of labels to match

        Returns:
            Metric value if found, None otherwise
        """
        for metric in metrics:
            if metric['name'] != metric_name:
                continue

            if labels:
                # Check if all required labels match
                if all(metric['labels'].get(k) == v for k, v in labels.items()):
                    return metric['value']
            else:
                # No label filtering
                return metric['value']

        return None

    def get_gateway_health(self) -> Dict:
        """
        Get basic gateway health metrics.

        Returns:
            Dict with health status and basic metrics
        """
        try:
            raw_metrics = self.fetch_raw_metrics()
            metrics = self.parse_metrics(raw_metrics)

            # Extract key metrics
            go_goroutines = self.get_metric_value(metrics, 'go_goroutines')
            go_memstats_alloc_bytes = self.get_metric_value(
                metrics, 'go_memstats_alloc_bytes'
            )

            # Count total requests across all endpoints
            total_requests = sum(
                m['value'] for m in metrics
                if m['name'] == 'krakend_router_requests_total'
            )

            return {
                'status': 'healthy',
                'uptime_available': True,
                'goroutines': int(go_goroutines) if go_goroutines else 0,
                'memory_bytes': int(go_memstats_alloc_bytes) if go_memstats_alloc_bytes else 0,
                'total_requests': int(total_requests),
                'metrics_count': len(metrics)
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }

    def get_request_metrics(self) -> Dict:
        """
        Get request-related metrics.

        Returns:
            Dict with request counts by status code
        """
        try:
            raw_metrics = self.fetch_raw_metrics()
            metrics = self.parse_metrics(raw_metrics)

            # Group requests by status code
            by_status = {}
            total = 0

            for metric in metrics:
                if metric['name'] == 'krakend_router_requests_total':
                    code = metric['labels'].get('code', 'unknown')
                    value = int(metric['value'])
                    by_status[code] = by_status.get(code, 0) + value
                    total += value

            return {
                'total_requests': total,
                'by_status_code': by_status,
                'success_rate': (by_status.get('200', 0) / total * 100) if total > 0 else 0
            }
        except Exception as e:
            return {'error': str(e)}

    def get_top_endpoints(self, limit: int = 10) -> Dict:
        """
        Get top endpoints by request count.

        Args:
            limit: Number of top endpoints to return

        Returns:
            Dict with top endpoints and their metrics
        """
        try:
            raw_metrics = self.fetch_raw_metrics()
            metrics = self.parse_metrics(raw_metrics)

            # Group requests by endpoint
            endpoint_stats = {}

            for metric in metrics:
                if metric['name'] == 'krakend_router_requests_total':
                    endpoint = metric['labels'].get('endpoint', 'unknown')
                    code = metric['labels'].get('code', 'unknown')
                    value = int(metric['value'])

                    if endpoint not in endpoint_stats:
                        endpoint_stats[endpoint] = {
                            'endpoint': endpoint,
                            'total_requests': 0,
                            'success_requests': 0,
                            'error_requests': 0,
                        }

                    endpoint_stats[endpoint]['total_requests'] += value

                    # Count success (2xx) vs errors (4xx, 5xx)
                    if code.startswith('2'):
                        endpoint_stats[endpoint]['success_requests'] += value
                    elif code.startswith('4') or code.startswith('5'):
                        endpoint_stats[endpoint]['error_requests'] += value

            # Calculate error rates and sort by total requests
            endpoints_list = []
            for endpoint_data in endpoint_stats.values():
                total = endpoint_data['total_requests']
                if total > 0:
                    endpoint_data['error_rate'] = (
                        endpoint_data['error_requests'] / total * 100
                    )
                else:
                    endpoint_data['error_rate'] = 0.0

                endpoints_list.append(endpoint_data)

            # Sort by total requests descending and limit
            endpoints_list.sort(key=lambda x: x['total_requests'], reverse=True)
            top_endpoints = endpoints_list[:limit]

            return {
                'endpoints': top_endpoints,
                'total_endpoints': len(endpoint_stats)
            }
        except Exception as e:
            return {'error': str(e), 'endpoints': [], 'total_endpoints': 0}
