#!/bin/bash
# ──────────────────────────────────────────────────────────────────
# 表現コード v1 の動作確認（どのモデルが作業していても、同じ結果になることを確かめる）。
#
#   bash _tools/expression/selftest.sh            # Short 2本と長尺1本（約20分）
#   bash _tools/expression/selftest.sh short      # Short だけ（u01・u09。約6分）
#
# u01（Short）と c01（長尺）の写しを _prototypes/expr_v1/pipeline_test/ に作り、
# 保存してある映像意図（_tools/expression/selftest/）を使って、本番と同じコマンド
# （run_shorts.sh／run_episode.sh）を v1 で最後まで走らせる。アップロードはしない。
# 最後に「SELFTEST PASS」が出れば合格。本番の回・予約済みの動画には触れない。
# ──────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")/../.."
WHAT="${1:-all}"
T=_prototypes/expr_v1/pipeline_test/s2_ura
FIX=_tools/expression/selftest
mkdir -p "$T"

echo "━━ 0. 日付の関門（expr_gate）の確認 ━━"
r1=$(EXPR_TODAY=2026-11-20 python3 _tools/expression/expr_gate.py s2_ura/u22_dummy --short short1 2>/dev/null)
r2=$(EXPR_TODAY=2026-12-07 python3 _tools/expression/expr_gate.py s2_ura/u01_jcpenney-sale --short short1 2>/dev/null)
r3=$(EXPR_TODAY=2026-12-07 python3 _tools/expression/expr_gate.py s2_ura/u22_dummy --short short1 2>/dev/null || echo fail)
[ "$r1" = current ] && [ "$r2" = current ] && [ "$r3" = fail ] || { echo "FAIL: expr_gate（$r1/$r2/$r3）"; exit 1; }
echo "OK：適用日より前＝現行／旧表現の回＝現行／適用日以降で映像意図なし＝不合格"

if [ "$WHAT" = all ] || [ "$WHAT" = short ]; then
  echo "━━ 1. Short（u01 の写し） ━━"
  U=$T/u01_jcpenney-sale; rm -rf "$U"; cp -r s2_ura/u01_jcpenney-sale "$U"
  rm -rf "$U"/shorts_build/short1/{publish_manifest.json,.work,*.mp4,built_readings.json} "$U"/quality_record.md
  cp $FIX/u01_visual_plan.json "$U/shorts_build/short1/visual_plan.json"
  EXPR_FORCE=1 bash _tools/pipeline/run_shorts.sh "$U"
  python3 -c "import json,sys;d=json.load(open(sys.argv[1]));assert d['pass'],d" "$U/shorts_build/short1/expr_record.json"
  echo "━━ 1b. Short（u09 の写し：写真の reset・compare_bars・quote・check。Opus の試作 2026-11-13） ━━"
  U=$T/u09_costco-hotdog; rm -rf "$U"; cp -r s2_ura/u09_costco-hotdog "$U"
  rm -rf "$U"/shorts_build/short1/{publish_manifest.json,.work,*.mp4,built_readings.json} "$U"/quality_record.md
  cp $FIX/u09_visual_plan.json "$U/shorts_build/short1/visual_plan.json"
  EXPR_FORCE=1 bash _tools/pipeline/run_shorts.sh "$U"
  python3 -c "import json,sys;d=json.load(open(sys.argv[1]));assert d['pass'],d" "$U/shorts_build/short1/expr_record.json"
fi
if [ "$WHAT" = all ] || [ "$WHAT" = long ]; then
  echo "━━ 2. 長尺（c01 の写し） ━━"
  C=$T/c01_jcpenney-fair-and-square; rm -rf "$C"; cp -r s2_ura/c01_jcpenney-fair-and-square "$C"
  rm -rf "$C"/{video_build,publish_manifest.json,quality_record.md}
  sed -i 's/--accent:#E11D48/--accent:#E11D49/' "$C/slide.html"      # 写しなので、色の重複検査に当たらない色にする
  cp $FIX/c01_visual_plan.json "$C/visual_plan.json"
  EXPR_FORCE=1 bash _tools/pipeline/run_episode.sh "$C"
  python3 -c "import json,sys;d=json.load(open(sys.argv[1]));assert d['pass'],d" "$C/expr_record.json"
fi
echo
echo "SELFTEST PASS（表現コード v1：$WHAT）"
