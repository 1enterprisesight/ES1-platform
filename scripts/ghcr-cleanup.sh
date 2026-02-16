#!/usr/bin/env bash
# scripts/ghcr-cleanup.sh — Delete old GHCR image versions, keeping only 'latest'
#
# Usage:
#   ./scripts/ghcr-cleanup.sh              # dry run (shows what would be deleted)
#   ./scripts/ghcr-cleanup.sh --delete     # actually delete
#
# Requires: gh CLI authenticated with delete:packages scope
#   gh auth refresh -s delete:packages

set -euo pipefail

OWNER="1enterprisesight"
DRY_RUN=true
[[ "${1:-}" == "--delete" ]] && DRY_RUN=false

# Get all es1-platform packages
packages=$(gh api "users/${OWNER}/packages?package_type=container" --paginate \
  --jq '.[].name' 2>/dev/null)

if [[ -z "$packages" ]]; then
  echo "No packages found for ${OWNER}"
  exit 1
fi

total_deleted=0
total_kept=0

for pkg in $packages; do
  pkg_encoded="${pkg//\//%2F}"
  echo ""
  echo "=== ${pkg} ==="

  # Get all versions (paginate to get them all)
  versions_json=$(gh api "users/${OWNER}/packages/container/${pkg_encoded}/versions?per_page=100" \
    --paginate 2>/dev/null || echo "[]")

  # Find the version ID tagged 'latest'
  latest_id=$(echo "$versions_json" | \
    jq -r '.[] | select(.metadata.container.tags | index("latest")) | .id' | head -1)

  if [[ -z "$latest_id" ]]; then
    echo "  WARNING: no 'latest' tag found — skipping (won't delete everything)"
    continue
  fi

  # Get all version IDs that are NOT the latest-tagged version
  delete_ids=$(echo "$versions_json" | \
    jq -r ".[] | select(.id != ${latest_id}) | .id")

  kept=1  # the latest one
  deleted=0

  for vid in $delete_ids; do
    [[ -z "$vid" ]] && continue
    tags=$(echo "$versions_json" | jq -r ".[] | select(.id == ${vid}) | .metadata.container.tags | join(\", \")")
    tags="${tags:-<untagged>}"

    if $DRY_RUN; then
      echo "  [DRY RUN] would delete version ${vid} (${tags})"
    else
      if gh api --method DELETE "users/${OWNER}/packages/container/${pkg_encoded}/versions/${vid}" 2>/dev/null; then
        echo "  deleted version ${vid} (${tags})"
      else
        echo "  FAILED to delete version ${vid} (${tags})"
      fi
    fi
    ((deleted++))
  done

  echo "  kept: ${kept}, deleted: ${deleted}"
  total_deleted=$((total_deleted + deleted))
  total_kept=$((total_kept + kept))
done

echo ""
echo "════════════════════════════════════"
echo "Total kept:    ${total_kept}"
echo "Total deleted: ${total_deleted}"
if $DRY_RUN; then
  echo ""
  echo "This was a DRY RUN. To actually delete, run:"
  echo "  $0 --delete"
fi
