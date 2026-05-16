#!/bin/bash
# build_animation.sh — アニメーション付きリファレンス動画を生成する
#
# 生成物: out/ep01_animation.mp4
#   - Playwright でスライドのアニメーション再生をそのまま録画
#   - 音声は durations.json のタイミングに完全同期
#   - コントロールパネル・ナレーション表示なし
#   - Font Awesome アイコンはローカル参照（CDN 不要）
#
# 前提: gen_audio.py で out/audio_XX.wav 生成済みであること
#
# Usage: bash build_animation.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EP_DIR="$(dirname "$SCRIPT_DIR")"
OUT="$SCRIPT_DIR/out"
RECORD_HTML="$EP_DIR/slide_record.html"

export NODE_PATH=/opt/node22/lib/node_modules
export PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers

echo "============================================"
echo "  ep01 Animation Video Builder v2"
echo "  Output: $OUT"
echo "============================================"

mkdir -p "$OUT"

# ── Step 0: 音声が未生成なら生成 ──────────────────────────────────────────────
if ! ls "$OUT"/audio_00.wav "$OUT"/audio_00.mp3 2>/dev/null | grep -q .; then
  echo ""
  echo "Step 0: Generating narration audio..."
  python3 "$SCRIPT_DIR/gen_audio.py" "$EP_DIR/slide.html" "$OUT"
fi

# ── Step 1: 録画用 HTML を生成（コントロール・ナレーションなし）────────────────
echo ""
echo "Step 1/4: Generating slide_record.html ..."
python3 "$SCRIPT_DIR/make_record_html.py" "$EP_DIR/slide.html" "$RECORD_HTML"

# ── Step 2: アニメーション録画 ───────────────────────────────────────────────
echo ""
echo "Step 2/4: Recording slide animation ..."
echo "  ※ 実時間での録画のためしばらくかかります"
node "$SCRIPT_DIR/record_animation.js" \
  "$RECORD_HTML" \
  "$OUT" \
  "$OUT/durations.json"

# ── Step 3: 音声ミックス（durations.json タイミング準拠）─────────────────────
echo ""
echo "Step 3/4: Mixing narration audio ..."
bash "$SCRIPT_DIR/mix_audio.sh" "$OUT"

# ── Step 4: 動画 + 音声を結合 ────────────────────────────────────────────────
echo ""
echo "Step 4/4: Combining video and audio ..."

WEBM="$OUT/slides_animation.webm"
AUDIO="$OUT/narration_mixed.wav"
OUTPUT="$OUT/ep01_animation.mp4"

ffmpeg -y \
  -i "$WEBM" \
  -i "$AUDIO" \
  -c:v libx264 -preset slow -crf 15 \
  -c:a aac -b:a 192k \
  -shortest \
  "$OUTPUT" 2>/dev/null

DUR=$(ffmpeg -i "$OUTPUT" 2>&1 | grep -oP 'Duration: \K[0-9:]+' | head -1)
SIZE=$(du -sh "$OUTPUT" | cut -f1)

echo ""
echo "============================================"
echo "  Build Complete!"
echo "============================================"
echo ""
echo "Animation video : $OUTPUT"
echo "Duration        : $DUR"
echo "Size            : $SIZE"
