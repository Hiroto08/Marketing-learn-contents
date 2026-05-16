#!/bin/bash
# mix_audio.sh — SLIDES_META のスタート時刻に合わせて各スライドの音声を配置し
#               ひとつのナレーション音声トラックに合成する。
#
# Usage: bash mix_audio.sh <out_dir>

set -e
OUT_DIR="${1:-out}"
FFMPEG="ffmpeg"

# SLIDES_META の start 時刻（秒）—— slide.html と完全一致させること
SLIDE_STARTS=(0 30 90 150 210 270 330 405 450 495 530 580)
NUM_SLIDES=12
TOTAL_SECS=605

# 音声ファイルの拡張子を判定
AUDIO_EXT="mp3"
if ls "$OUT_DIR"/audio_00.wav 2>/dev/null | grep -q .; then
  AUDIO_EXT="wav"
fi

echo "Mixing $NUM_SLIDES narration files (audio format: $AUDIO_EXT) ..."

# ffmpeg の -i リストと filter_complex 文字列を生成
INPUTS=""
FILTER=""
AMIX_IN=""

for i in $(seq 0 $((NUM_SLIDES - 1))); do
  IDX=$(printf "%02d" "$i")
  FILE="$OUT_DIR/audio_${IDX}.${AUDIO_EXT}"
  DELAY_MS=$(( SLIDE_STARTS[$i] * 1000 ))

  INPUTS="$INPUTS -i $FILE"
  FILTER="${FILTER}[$i:a]adelay=${DELAY_MS}|${DELAY_MS}[a${i}];"
  AMIX_IN="${AMIX_IN}[a${i}]"
done

# amix で全トラックを合成（normalize=0 で各トラックの音量を下げない）
FILTER="${FILTER}${AMIX_IN}amix=inputs=${NUM_SLIDES}:normalize=0[aout]"

OUT_WAV="$OUT_DIR/narration_mixed.wav"

$FFMPEG -y $INPUTS \
  -filter_complex "$FILTER" \
  -map "[aout]" \
  -t $TOTAL_SECS \
  "$OUT_WAV" 2>/dev/null

DUR=$($FFMPEG -i "$OUT_WAV" 2>&1 | grep -oP 'Duration: \K[0-9:]+' | head -1)
SIZE=$(du -sh "$OUT_WAV" | cut -f1)
echo "Mixed audio: $OUT_WAV (duration=$DUR, size=$SIZE)"
