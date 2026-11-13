#!/bin/bash
# 試作ビルド（Before＝今の表現／After＝表現コード v1）。台本・声は同じ。アップロードしない。
set -e
U=$1; ANSWER=$2
B=_prototypes/expr_v1/before/$U/shorts_build/short1; A=_prototypes/expr_v1/after/$U/shorts_build/short1
python3 _tools/video/make_video.py $B/stage.html --out $B --speaker 11 --speed 1.15 --lead 0.15 --intro 0.3 --outro 0.5 --final-outro 1.2 --width 1080 --height 1920 --bgm _assets/audio/bgm_calm_loop.wav --sfx-dir _assets/audio
python3 _tools/video/make_video.py $A/stage.html --out $A --speaker 11 --speed 1.15 --lead 0.15 --intro 0.0 --outro 0.5 --final-outro 0.6 --width 1080 --height 1920 --expr v1 --num-gap 0.6 --beat "$ANSWER" --answer-text "$ANSWER"
