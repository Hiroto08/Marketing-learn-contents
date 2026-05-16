#!/bin/bash
# build_animation.sh — アニメーション付きリファレンス動画を生成する
#
# 生成物: out/ep01_animation.mp4
#   - Playwright でスライドのアニメーション再生をそのまま録画
#   - SLIDES_META のタイミングに合わせた読み上げ音声を合成
#
# 音声は事前に gen_audio.py で生成済みであること（out/audio_XX.wav/.mp3）
# 未生成の場合は先に実行する:
#   python3 gen_audio.py ../slide.html out [speaker_id]
#
# Usage:
#   bash build_animation.sh [total_secs]
#   total_secs: 録画秒数（デフォルト: 605 = スライド600秒+余白5秒）

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EP_DIR="$(dirname "$SCRIPT_DIR")"
OUT="$SCRIPT_DIR/out"
TOTAL="${1:-605}"

export NODE_PATH=/opt/node22/lib/node_modules
export PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers

echo "============================================"
echo "  ep01 Animation Video Builder"
echo "  Total duration: ${TOTAL}s"
echo "  Output: $OUT"
echo "============================================"

mkdir -p "$OUT"

# ── Step 1: 音声が未生成なら生成 ──────────────────────────────────────────────
if ! ls "$OUT"/audio_00.wav "$OUT"/audio_00.mp3 2>/dev/null | grep -q .; then
  echo ""
  echo "Step 0: Generating narration audio first..."
  python3 "$SCRIPT_DIR/gen_audio.py" "$EP_DIR/slide.html" "$OUT"
fi

# ── Step 2: アニメーション録画 ───────────────────────────────────────────────
echo ""
echo "Step 1/3: Recording slide animation (${TOTAL}s) ..."
echo "  ※ 実時間での録画のためしばらくかかります"
node "$SCRIPT_DIR/record_animation.js" "$EP_DIR/slide.html" "$OUT" "$TOTAL"

# ── Step 3: ナレーション音声をタイミングに合わせてミックス ───────────────────
echo ""
echo "Step 2/3: Mixing narration audio ..."
bash "$SCRIPT_DIR/mix_audio.sh" "$OUT"

# ── Step 4: 動画 + 音声を結合 ────────────────────────────────────────────────
echo ""
echo "Step 3/3: Combining video and audio ..."

WEBM="$OUT/slides_animation.webm"
AUDIO="$OUT/narration_mixed.wav"
OUTPUT="$OUT/ep01_animation.mp4"

ffmpeg -y \
  -i "$WEBM" \
  -i "$AUDIO" \
  -c:v libx264 -preset fast -crf 18 \
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
echo ""
echo "使い方:"
echo "  1. ep01_animation.mp4 を再生してアニメーションとナレーションを確認"
echo "  2. 各スライドの尺を参考に自分の声でナレーションを収録"
echo "  3. 動画編集ソフトで音声トラックを差し替えて完成"
