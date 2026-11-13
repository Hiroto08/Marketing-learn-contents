#!/bin/bash
# After（表現コード v1）と 素材組み込み版 を作り直す。アップロードしない。
set -e
U=u01_jcpenney-sale; ANS="得した気分を買っていた"
OPT="--speaker 11 --speed 1.15 --lead 0.15 --intro 0.0 --outro 0.5 --final-outro 0.6 --width 1080 --height 1920 --expr v1 --num-gap 0.6"
for v in after visual; do
  D=_prototypes/expr_v1/$v/$U/shorts_build/short1
  if [ $v = visual ]; then python3 _tools/expression/apply_expr.py s2_ura/$U/shorts_build/short1/stage.html $D/stage.html --kind short --series "売れる仕組みの裏側" --no "#01" --visuals _prototypes/expr_v1/assets_u01/visual_plan.json
  else python3 _tools/expression/apply_expr.py s2_ura/$U/shorts_build/short1/stage.html $D/stage.html --kind short --series "売れる仕組みの裏側" --no "#01"; fi
  python3 _tools/video/make_video.py $D/stage.html --out $D $OPT --beat "$ANS" --answer-text "$ANS"
done
C=c01_jcpenney-fair-and-square; A=_prototypes/expr_v1/after/$C
python3 _tools/expression/apply_expr.py s2_ura/$C/slide.html $A/slide.html --kind long --series "売れる仕組みの裏側" --no "CASE FILE #01"
python3 _tools/video/make_video.py $A/slide.html --out $A/video_build/out --speaker 11 --speed 1.1 --final-outro 3.0 --lead 0.3 --intro 0.3 --expr v1 --num-gap 0.7 --beat "得した気分を買っていました" --answer-text "得した気分を買っていた"
