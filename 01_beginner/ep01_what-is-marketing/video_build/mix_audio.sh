#!/bin/bash
# mix_audio.sh — durations.json の実際の音声長からタイミングを計算して
#               各スライドの音声をひとつの WAV に合成する。
#
# Usage: bash mix_audio.sh <out_dir>

set -e
OUT_DIR="${1:-out}"
FFMPEG="ffmpeg"
DURATIONS_JSON="$OUT_DIR/durations.json"

if [ ! -f "$DURATIONS_JSON" ]; then
  echo "ERROR: $DURATIONS_JSON not found. Run gen_audio.py first."
  exit 1
fi

# durations.json からスライド数・開始時刻・合計時間を取得
read -r NUM_SLIDES TOTAL_SECS STARTS_CSV <<< "$(python3 - "$DURATIONS_JSON" <<'PYEOF'
import json, sys
with open(sys.argv[1]) as f:
    d = json.load(f)
durs = d["durations"]
n = len(durs)
starts = []
t = 0.0
for i in range(n):
    starts.append(t)
    t += durs[str(i)]
total = int(t) + 3
starts_csv = ",".join(f"{s:.3f}" for s in starts)
print(n, total, starts_csv)
PYEOF
)"

IFS=',' read -ra SLIDE_STARTS <<< "$STARTS_CSV"
echo "Slides: $NUM_SLIDES | Total: ${TOTAL_SECS}s"
echo "Start times: ${STARTS_CSV}"

# 音声ファイルの拡張子を判定
AUDIO_EXT="mp3"
if ls "$OUT_DIR"/audio_00.wav 2>/dev/null | grep -q .; then
  AUDIO_EXT="wav"
fi
echo "Audio format: $AUDIO_EXT"

# ffmpeg の -i リストと filter_complex を生成
INPUTS=""
FILTER=""
AMIX_IN=""

for i in $(seq 0 $((NUM_SLIDES - 1))); do
  IDX=$(printf "%02d" "$i")
  FILE="$OUT_DIR/audio_${IDX}.${AUDIO_EXT}"
  START="${SLIDE_STARTS[$i]}"
  DELAY_MS=$(python3 -c "print(int(float('$START') * 1000))")

  INPUTS="$INPUTS -i $FILE"
  FILTER="${FILTER}[$i:a]adelay=${DELAY_MS}|${DELAY_MS}[a${i}];"
  AMIX_IN="${AMIX_IN}[a${i}]"
done

FILTER="${FILTER}${AMIX_IN}amix=inputs=${NUM_SLIDES}:normalize=0[aout]"

OUT_WAV="$OUT_DIR/narration_mixed.wav"

$FFMPEG -y $INPUTS \
  -filter_complex "$FILTER" \
  -map "[aout]" \
  -t "$TOTAL_SECS" \
  "$OUT_WAV" 2>/dev/null

DUR=$($FFMPEG -i "$OUT_WAV" 2>&1 | grep -oP 'Duration: \K[0-9:]+' | head -1)
SIZE=$(du -sh "$OUT_WAV" | cut -f1)
echo "Mixed audio: $OUT_WAV (duration=$DUR, size=$SIZE)"
