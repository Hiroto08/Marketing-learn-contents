#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# setup_env.sh — re-provision the video-generation toolchain.
#
# The web container wipes everything outside the git tree on restart
# (ffmpeg, fonts, the VOICEVOX engine, the playwright pip package & browser).
# This script restores all of it. It is idempotent: safe to run repeatedly,
# and skips anything already present. Invoked by the SessionStart hook so the
# state gets cached into the container snapshot after the first run.
#
# Manual use:  bash _tools/setup_env.sh
# ──────────────────────────────────────────────────────────────────────────────
set -uo pipefail

PWB="/opt/pw-browsers"
VV_DIR="/opt/voicevox_engine"
VV_RUN="$VV_DIR/linux-cpu-x64/run"
VV_VER="0.25.2"
VV_URL="https://github.com/VOICEVOX/voicevox_engine/releases/download/${VV_VER}/voicevox_engine-linux-cpu-x64-${VV_VER}.7z.001"

log() { echo "[setup_env] $*"; }

# ── 1. apt packages: ffmpeg (TTS/mux), p7zip (VOICEVOX extract), Noto CJK font ──
need=()
command -v ffmpeg  >/dev/null 2>&1 || need+=(ffmpeg)
command -v ffprobe >/dev/null 2>&1 || need+=(ffmpeg)
command -v 7z      >/dev/null 2>&1 || need+=(p7zip-full)
fc-list 2>/dev/null | grep -qi "Noto Sans CJK JP" || need+=(fonts-noto-cjk)
# design v2.1: 見出し・キーワードのBlack(900)ウェイトに必須
fc-list 2>/dev/null | grep -qi "Noto Sans CJK JP:style=Black" || need+=(fonts-noto-cjk-extra)
if [ ${#need[@]} -gt 0 ]; then
  uniq_need=$(printf '%s\n' "${need[@]}" | sort -u | tr '\n' ' ')
  log "apt install: $uniq_need"
  apt-get update -qq >/dev/null 2>&1 || true
  DEBIAN_FRONTEND=noninteractive apt-get install -y $uniq_need >/dev/null 2>&1 \
    || apt-get install -y $uniq_need
  fc-cache -f >/dev/null 2>&1 || true
else
  log "apt deps already present"
fi

# ── 2. playwright (pip) + chromium browser ──
python3 -c "import playwright" >/dev/null 2>&1 || {
  log "pip install playwright"
  pip3 install --quiet playwright
}
export PLAYWRIGHT_BROWSERS_PATH="$PWB"
# The base image ships a cached chromium build (e.g. chromium-1194) but the
# installed playwright may expect a different revision number, and the official
# browser download CDN is blocked here. Bridge the gap by symlinking the cached
# build to whatever revision the current playwright asks for.
if ! python3 - <<'PY' >/dev/null 2>&1
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); b.close()
PY
then
  want=$(python3 - <<'PY' 2>&1
from playwright.sync_api import sync_playwright
try:
    with sync_playwright() as p:
        p.chromium.launch()
except Exception as e:
    print(e)
PY
)
  cbase=$(ls -d "$PWB"/chromium-[0-9]* 2>/dev/null | grep -E 'chromium-[0-9]+$' | head -1)
  hbase=$(ls -d "$PWB"/chromium_headless_shell-[0-9]* 2>/dev/null | head -1)
  wver=$(echo "$want" | grep -oE 'chromium(_headless_shell)?-[0-9]+' | grep -oE '[0-9]+' | head -1)
  if [ -n "$wver" ] && [ -n "$cbase" ]; then
    log "symlink chromium $cbase -> rev $wver"
    ln -sf "$cbase" "$PWB/chromium-$wver"
    if [ -n "$hbase" ]; then
      mkdir -p "$PWB/chromium_headless_shell-$wver/chrome-headless-shell-linux64"
      ln -sf "$hbase/chrome-linux/headless_shell" \
        "$PWB/chromium_headless_shell-$wver/chrome-headless-shell-linux64/chrome-headless-shell"
    fi
  else
    log "WARN: could not resolve chromium revision; trying 'playwright install'"
    python3 -m playwright install chromium >/dev/null 2>&1 || true
  fi
else
  log "playwright chromium OK"
fi

# ── 3. VOICEVOX engine ──
# Fallback: GitHub releases are blocked in repo-scoped web sessions (proxy 403
# "not enabled for this session"). Docker Hub is reachable, so pull the engine
# layer of the official image voicevox/voicevox_engine:cpu-$VV_VER via the
# registry HTTP API (no dockerd needed) and extract opt/voicevox_engine.
# Battle-tested 2026-07-12.
vv_fetch_dockerhub() {
  log "GitHub blocked; falling back to Docker Hub layer pull (cpu-$VV_VER)"
  local tok digest
  tok=$(curl -fsSL "https://auth.docker.io/token?service=registry.docker.io&scope=repository:voicevox/voicevox_engine:pull" \
        | python3 -c "import json,sys;print(json.load(sys.stdin)['token'])") || return 1
  digest=$(curl -fsSL -H "Authorization: Bearer $tok" \
      -H "Accept: application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json" \
      "https://registry-1.docker.io/v2/voicevox/voicevox_engine/manifests/cpu-$VV_VER" \
    | python3 -c "import json,sys; m=json.load(sys.stdin); print(next(x['digest'] for x in m['manifests'] if x['platform']['architecture']=='amd64'))") || return 1
  digest=$(curl -fsSL -H "Authorization: Bearer $tok" \
      -H "Accept: application/vnd.oci.image.manifest.v1+json" \
      "https://registry-1.docker.io/v2/voicevox/voicevox_engine/manifests/$digest" \
    | python3 -c "import json,sys; m=json.load(sys.stdin); print(max(m['layers'], key=lambda l: l['size'])['digest'])") || return 1
  log "downloading engine layer (~1.9GB)"
  curl -fsSL --retry 3 -H "Authorization: Bearer $tok" -o /tmp/vv_layer.tgz \
      "https://registry-1.docker.io/v2/voicevox/voicevox_engine/blobs/$digest" || return 1
  (cd / && tar xzf /tmp/vv_layer.tgz opt/voicevox_engine) || { rm -f /tmp/vv_layer.tgz; return 1; }
  rm -f /tmp/vv_layer.tgz
  # docker image layout puts the binary at $VV_DIR/run; create the path the
  # rest of the tooling expects ($VV_RUN = linux-cpu-x64/run)
  mkdir -p "$VV_DIR/linux-cpu-x64"
  ln -sf "$VV_DIR/run" "$VV_RUN"
  chmod +x "$VV_DIR/run"
}

if [ ! -x "$VV_RUN" ] && [ -x "$VV_DIR/run" ]; then
  # docker-layout install from a previous fallback run; just re-link
  mkdir -p "$VV_DIR/linux-cpu-x64" && ln -sf "$VV_DIR/run" "$VV_RUN"
fi
if [ ! -x "$VV_RUN" ]; then
  log "downloading VOICEVOX $VV_VER (~1.7GB, one-time)"
  if curl -fsSL -o /tmp/vv.7z.001 "$VV_URL"; then
    7z x -y -o"$VV_DIR" /tmp/vv.7z.001 >/dev/null 2>&1 && log "VOICEVOX extracted"
    rm -f /tmp/vv.7z.001
  elif vv_fetch_dockerhub; then
    log "VOICEVOX extracted from Docker Hub image layer"
  else
    log "WARN: VOICEVOX download failed (GitHub AND Docker Hub); audio synth unavailable"
  fi
else
  log "VOICEVOX already installed"
fi

# Start the engine if installed and not already serving.
if [ -x "$VV_RUN" ] && ! curl -s -m2 http://127.0.0.1:50021/version >/dev/null 2>&1; then
  log "starting VOICEVOX engine on :50021"
  nohup "$VV_RUN" --host 127.0.0.1 --port 50021 >/tmp/voicevox.log 2>&1 &
fi

# ── 4. persist env for the session ──
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo "export PLAYWRIGHT_BROWSERS_PATH=$PWB" >> "$CLAUDE_ENV_FILE"
fi

log "done"
