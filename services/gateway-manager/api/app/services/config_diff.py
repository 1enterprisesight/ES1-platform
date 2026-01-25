"""
Config Diff Helper

Compares KrakenD configurations to identify what changed (added, removed, modified endpoints).
Used to generate exposure_changes records for audit trail.
"""

from typing import List, Dict, Any


def compare_configs(active_config: Dict[str, Any], draft_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Compare active vs draft configs to generate exposure_changes records

    Args:
        active_config: Currently active KrakenD configuration
        draft_config: Proposed draft configuration

    Returns:
        List of changes with format:
        [
            {
                'type': 'add' | 'remove' | 'modify',
                'endpoint': '/endpoint/path',
                'settings_before': {...} or None,
                'settings_after': {...} or None
            }
        ]
    """
    changes = []

    # Extract endpoints from both configs
    active_endpoints = {ep['endpoint']: ep for ep in active_config.get('endpoints', [])}
    draft_endpoints = {ep['endpoint']: ep for ep in draft_config.get('endpoints', [])}

    # Find added endpoints (in draft but not in active)
    for endpoint, config in draft_endpoints.items():
        if endpoint not in active_endpoints:
            changes.append({
                'type': 'add',
                'endpoint': endpoint,
                'settings_before': None,
                'settings_after': config
            })

    # Find removed endpoints (in active but not in draft)
    for endpoint, config in active_endpoints.items():
        if endpoint not in draft_endpoints:
            changes.append({
                'type': 'remove',
                'endpoint': endpoint,
                'settings_before': config,
                'settings_after': None
            })

    # Find modified endpoints (in both but different config)
    for endpoint in set(active_endpoints) & set(draft_endpoints):
        if active_endpoints[endpoint] != draft_endpoints[endpoint]:
            changes.append({
                'type': 'modify',
                'endpoint': endpoint,
                'settings_before': active_endpoints[endpoint],
                'settings_after': draft_endpoints[endpoint]
            })

    return changes
