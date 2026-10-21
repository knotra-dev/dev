#!/usr/bin/env bash
set -euo pipefail

workspace_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$workspace_dir/repos/engine"
bin/knotra serve --profile examples/local/profile.yaml \
  --data-dir "$workspace_dir/.state/engine" --cors-origin http://127.0.0.1:1420 &
engine_pid=$!

cleanup() {
  kill "$engine_pid" 2>/dev/null || true
  wait "$engine_pid" 2>/dev/null || true
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

cd "$workspace_dir/repos/desktop"
bun run desktop:dev
