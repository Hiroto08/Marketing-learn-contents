#!/bin/bash
# assemble_video.sh — スライド画像 + 音声を ffmpeg で結合してリファレンス動画を生成する
set -e

OUT_DIR="${1:-out}"
FFMPEG="ffmpeg"
NUM_SLIDES=12

echo "=== Video Assembly ==="

# 音声ファイルの拡張子を判定（VOICEVOX=wav / gtts=mp3）
AUDIO_EXT="mp3"
if ls "$OUT_DIR"/audio_00.wav 2>/dev/null | grep -q .; then
  AUDIO_EXT="wav"
fi
echo "Audio format: $AUDIO_EXT"

# 各スライドのセグメントを生成
CONCAT_LIST="$OUT_DIR/concat_list.txt"
> "$CONCAT_LIST"

SUCCESS_COUNT=0
for i in $(seq 0 $((NUM_SLIDES - 1))); do
  IDX=$(printf "%02d" "$i")
  SLIDE="$OUT_DIR/slide_${IDX}.png"
  AUDIO="$OUT_DIR/audio_${IDX}.${AUDIO_EXT}"
  SEGMENT="$OUT_DIR/segment_${IDX}.mp4"

  if [ ! -f "$SLIDE" ] || [ ! -f "$AUDIO" ]; then
    echo "  [WARNING] Missing files for slide $((i+1)), skipping"
    continue
  fi

  echo -n "  Segment $((i+1))/$NUM_SLIDES ..."

  $FFMPEG -y \
    -loop 1 -framerate 2 -i "$SLIDE" \
    -i "$AUDIO" \
    -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p \
    -vf "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black" \
    -c:a aac -b:a 192k \
    -shortest \
    "$SEGMENT" 2>/dev/null \
  && echo " ✓" \
  || { echo " FAILED"; continue; }

  echo "file '$(realpath "$SEGMENT")'" >> "$CONCAT_LIST"
  SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
done

if [ "$SUCCESS_COUNT" -eq 0 ]; then
  echo "ERROR: No segments generated."
  exit 1
fi

# セグメントを結合
OUTPUT="$OUT_DIR/ep01_reference.mp4"
echo "Concatenating $SUCCESS_COUNT segments ..."
$FFMPEG -y -f concat -safe 0 -i "$CONCAT_LIST" \
  -c:v libx264 -preset veryfast -crf 18 \
  -c:a aac -b:a 192k \
  "$OUTPUT" 2>/dev/null

# 動画情報を表示
DUR=$($FFMPEG -i "$OUTPUT" 2>&1 | grep -oP 'Duration: \K[0-9:]+' | head -1)
SIZE=$(du -sh "$OUTPUT" | cut -f1)
echo ""
echo "=== Output ==="
echo "  File    : $OUTPUT"
echo "  Duration: $DUR"
echo "  Size    : $SIZE"
