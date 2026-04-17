#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mirror_dir="$repo_root/codex"
target_dir="$repo_root/.codex"

if [[ ! -d "$mirror_dir" ]]; then
  echo "Missing mirror dir: $mirror_dir" >&2
  exit 1
fi

mkdir -p "$target_dir"
rsync -a --delete "$mirror_dir/" "$target_dir/"

echo "Synced $mirror_dir -> $target_dir"
