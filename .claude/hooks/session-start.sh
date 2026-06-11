#!/bin/bash
# SessionStart hook — re-provision the video-generation toolchain.
# Runs automatically on every Claude Code web session start.
# Delegates to _tools/setup_env.sh which is idempotent.
set -uo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

REPO_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
bash "$REPO_DIR/_tools/setup_env.sh"
