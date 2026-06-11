#!/bin/bash
# Re-provision the video-generation toolchain on every container start.
# The web container wipes /opt and pip state between restarts; this hook
# restores everything (ffmpeg, Noto CJK font, playwright, VOICEVOX engine).
set -uo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

echo '{"async": true, "asyncTimeout": 300000}'

exec bash "$CLAUDE_PROJECT_DIR/_tools/setup_env.sh"
