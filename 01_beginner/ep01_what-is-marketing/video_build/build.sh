#!/bin/bash
# build.sh — ep01 リファレンス動画を生成するメインスクリプト
#
# VOICEVOX が起動している場合は自動的に使用する。
# 起動していない場合は Google TTS（gtts）にフォールバック。
#
# VOICEVOX を使う場合は事前に起動しておく:
#   # デスクトップ版: VOICEVOX アプリを起動
#   # Docker 版:
#   #   docker run -d -p 50021:50021 voicevox/voicevox_engine:cpu-ubuntu20.04-latest
#
# Usage:
#   bash build.sh [voicevox_speaker_id]
#
# Speaker IDs (主なもの):
#    1 = ずんだもん（ノーマル）
#    2 = 四国めたん（ノーマル）
#   13 = 青山龍星（ノーマル）← デフォルト、落ち着いた男性声
#   23 = 白上虎太郎（ノーマル）

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EP_DIR="$(dirname "$SCRIPT_DIR")"
OUT="$SCRIPT_DIR/out"
SPEAKER="${1:-13}"

export NODE_PATH=/opt/node22/lib/node_modules
export PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers

echo "============================================"
echo "  ep01 Reference Video Builder"
echo "  Speaker ID: $SPEAKER"
echo "  Output: $OUT"
echo "============================================"

mkdir -p "$OUT"

# ── Step 1: 音声生成 ─────────────────────────────────────────────────────────
echo ""
echo "Step 1/3: Generating narration audio..."
python3 "$SCRIPT_DIR/gen_audio.py" "$EP_DIR/slide.html" "$OUT" "$SPEAKER"

# ── Step 2: スライドスクリーンショット ────────────────────────────────────────
echo ""
echo "Step 2/3: Capturing slide screenshots..."
node "$SCRIPT_DIR/screenshot_slides.js" "$EP_DIR/slide.html" "$OUT"

# ── Step 3: 動画合成 ─────────────────────────────────────────────────────────
echo ""
echo "Step 3/3: Assembling video..."
bash "$SCRIPT_DIR/assemble_video.sh" "$OUT"

# ── 完了 ─────────────────────────────────────────────────────────────────────
echo ""
echo "============================================"
echo "  Build Complete!"
echo "============================================"
echo ""
echo "Reference video : $OUT/ep01_reference.mp4"
echo "Audio files     : $OUT/audio_00.{wav,mp3} 〜 audio_11.{wav,mp3}"
echo ""
echo "使い方:"
echo "  1. ep01_reference.mp4 を再生して各スライドの尺を確認する"
echo "  2. 自分の声で同じテキストを同じ尺で収録する"
echo "  3. DAW・動画編集ソフトで音声を差し替えて完成"
