#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# run_shorts.sh — エピソードのShortsを「生成→QA→縦型ビルド→A/V検証→(アップロード)」まで一気通貫。
#
#   bash _tools/pipeline/run_shorts.sh <episode_dir> [--upload]
#
# 前提: <episode_dir>/shorts_build/shortN/spec.py が存在すること（Nは1〜）。
#       spec.py の書き方は _tools/shorts_template/gen_stage.py 冒頭のdocstring参照。
#       台本(shorts.md)とspecのNARRATIONSは文字単位で一致していること（verifyが検査する）。
# アップロードのクォータ: 動画1本=1600単位/日10,000 → 1日6本まで。
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")/../.."

EP="${1:?usage: run_shorts.sh <episode_dir> [--upload]}"
EP="${EP%/}"
UPLOAD="${2:-}"

step() { echo; echo "━━ $* ━━"; }

step "0/4 VOICEVOX 起動確認"
if ! curl -s -m3 http://127.0.0.1:50021/version >/dev/null; then
  bash _tools/setup_env.sh
  for i in $(seq 1 30); do curl -s -m3 http://127.0.0.1:50021/version >/dev/null && break; sleep 5; done
fi
curl -s -m3 http://127.0.0.1:50021/version || { echo "FAIL: VOICEVOXが起動しない"; exit 1; }

specs=("$EP"/shorts_build/short*/spec.py)
[ -e "${specs[0]}" ] || { echo "FAIL: $EP/shorts_build/short*/spec.py が無い（yt-shorts-designer工程が未了）"; exit 1; }

for spec in "${specs[@]}"; do
  d="$(dirname "$spec")"
  name="$(basename "$d")"

  step "$name 1/4 stage生成 (gen_stage)"
  python3 _tools/shorts_template/gen_stage.py "$spec" "$d/stage.html"

  step "$name 2/4 QA (verify_shorts 9項目)"
  python3 _tools/checks/verify_shorts.py "$d"

  step "$name 3/4 縦型ビルド (1080x1920)"
  python3 _tools/video/make_video.py "$d/stage.html" \
    --out "$d" --speaker 11 --speed 1.15 \
    --lead 1.2 --intro 0.3 --outro 0.5 --final-outro 1.2 \
    --width 1080 --height 1920 \
    --bgm _assets/audio/bgm_calm_loop.wav --sfx-dir _assets/audio

  step "$name 4/4 A/V・ストリーム検証"
  python3 - "$d" "$name" <<'PY'
import glob, os, subprocess, sys
d, name = sys.argv[1], sys.argv[2]
f = f"{d}/{name}_final.mp4"
def dur(sel):
    out = subprocess.run(["ffprobe","-v","error","-select_streams",sel,
        "-show_entries","stream=duration","-of","default=noprint_wrappers=1:nokey=1",f],
        capture_output=True, text=True).stdout.strip()
    return float(out) if out else 0.0
v, a = dur("v:0"), dur("a:0")
missing = [os.path.basename(s) for s in sorted(glob.glob(f"{d}/.work/slides/slide_*.mp4"))
           if set(subprocess.run(["ffprobe","-v","error","-show_entries","stream=codec_type",
               "-of","csv=p=0",s],capture_output=True,text=True).stdout.split()) < {"video","audio"}]
print(f"dur={v:.2f}s av_diff={abs(v-a):.3f}s missing={missing}")
assert abs(v-a) <= 0.1, "A/V差>0.1s"
assert 15 <= v <= 30, "尺が15〜30秒の外"
assert not missing, f"videoストリーム欠落: {missing}（該当slide_NN.mp4を消して --slide N で再録画）"
print("OK")
PY
done

if [ "$UPLOAD" = "--upload" ]; then
  step "アップロード (private)"
  python3 _tools/publish/upload_youtube.py --shorts "$EP" --dry-run
  python3 _tools/publish/upload_youtube.py --shorts "$EP"
  echo "※ publish_manifest.json をコミット。Studioで各Shortに関連動画リンク（本編）を手動設定"
else
  step "アップロードはスキップ（--upload を付けると実行。1日6本のクォータに注意）"
fi

echo
echo "SHORTS PIPELINE PASS: $EP"
