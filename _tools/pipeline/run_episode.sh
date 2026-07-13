#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# run_episode.sh — 本編を「QA→ビルド→後処理→サムネ→(アップロード)」まで一気通貫で実行。
#
#   bash _tools/pipeline/run_episode.sh <episode_dir> [--upload]
#
# 前提: script.md / slide.html / description.md / thumbnail.md が完成していること
#       （制作そのものは episode-production スキル。これは製造ラインの実行だけ）
# 各ステップは機械ゲート。FAILで即停止するので、出力の指示に従って直してから再実行する。
# 全ステップ冪等（再実行安全）。ビルドは30分程度かかる。
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")/../.."   # リポジトリルートへ

EP="${1:?usage: run_episode.sh <episode_dir> [--upload]}"
EP="${EP%/}"
UPLOAD="${2:-}"

step() { echo; echo "━━ $* ━━"; }

step "0/5 VOICEVOX 起動確認"
if ! curl -s -m3 http://127.0.0.1:50021/version >/dev/null; then
  echo "VOICEVOX停止中 → setup_env.sh を実行（初回はDL~1.9GBで数分かかる）"
  bash _tools/setup_env.sh
  for i in $(seq 1 30); do curl -s -m3 http://127.0.0.1:50021/version >/dev/null && break; sleep 5; done
fi
curl -s -m3 http://127.0.0.1:50021/version || { echo "FAIL: VOICEVOXが起動しない (/tmp/voicevox.log 参照)"; exit 1; }

step "1/5 QA (verify_episode)"
python3 _tools/checks/verify_episode.py "$EP"

step "2/5 ビルド (make_video: BGM+SFXミックス込みのシリーズ標準)"
python3 _tools/video/make_video.py "$EP/slide.html" \
  --out "$EP/video_build/out" --speaker 11 --speed 1.1 --final-outro 3.0 \
  --bgm _assets/audio/bgm_calm_loop.wav --sfx-dir _assets/audio

step "3/5 後処理 (A/V検証・LUFS・タイムスタンプ実測修正・ステージング)"
python3 _tools/video/postbuild_episode.py "$EP"

step "4/5 サムネイル生成"
if [ ! -f "$EP/thumbnail.png" ]; then
  python3 _tools/publish/make_thumbnail.py "$EP"
  echo "※ 生成した $EP/thumbnail.png をReadで目視確認し、script/description の変更と一緒にコミットすること"
else
  echo "既存の $EP/thumbnail.png を使用（作り直しは make_thumbnail.py を直接実行）"
fi

if [ "$UPLOAD" = "--upload" ]; then
  step "5/5 アップロード (private・サムネ自動設定)"
  python3 _tools/publish/upload_youtube.py --episode "$EP" --dry-run
  python3 _tools/publish/upload_youtube.py --episode "$EP"
  echo "※ publish_manifest.json をコミットすること"
else
  step "5/5 アップロードはスキップ（--upload を付けると実行）"
fi

echo
echo "EPISODE PIPELINE PASS: $EP"
echo "残りの手作業: タイムスタンプ/サムネ/manifestのコミット・push、Studioで公開確認"
