#!/usr/bin/env bash
set -euo pipefail

base_ref="${1:-origin/main}"
config_path=".gitleaks.toml"

if ! command -v gitleaks >/dev/null 2>&1; then
  echo "gitleaks is not installed."
  echo "Install from official releases: https://github.com/gitleaks/gitleaks/releases"
  exit 1
fi

if [[ ! -f "${config_path}" ]]; then
  echo "Missing gitleaks config: ${config_path}"
  exit 1
fi

if ! git rev-parse --verify "${base_ref}" >/dev/null 2>&1; then
  echo "Base ref '${base_ref}' not found locally."
  echo "Run: git fetch origin main"
  exit 1
fi

base_sha="$(git merge-base "${base_ref}" HEAD)"
if [[ -z "${base_sha}" ]]; then
  echo "Unable to compute merge-base for '${base_ref}' and HEAD."
  exit 1
fi

log_range="${base_sha}..HEAD"
echo "Running gitleaks over range: ${log_range}"

gitleaks git \
  --redact \
  --verbose \
  --config "${config_path}" \
  --log-opts="${log_range}"
