#!/bin/sh
set -eu

tmpdir="$(mktemp -d)"
cleanup() {
  /workspace/node_modules/.bin/supabase stop --no-backup >/tmp/supabase-stop.log 2>&1 || true
}

trap cleanup EXIT

cd "$tmpdir"
/workspace/node_modules/.bin/supabase init --force >/tmp/supabase-init.log 2>&1
if ! /workspace/node_modules/.bin/supabase start >/tmp/supabase-start.log 2>&1; then
  echo "supabase start failed"
  cat /tmp/supabase-start.log
  exit 1
fi
if ! /workspace/node_modules/.bin/supabase status >/tmp/supabase-status.log 2>&1; then
  echo "supabase status failed"
  cat /tmp/supabase-status.log
  exit 1
fi
test -f supabase/config.toml
test -s /tmp/supabase-start.log
test -s /tmp/supabase-status.log
printf '%s\n' "Supabase start smoke OK"
