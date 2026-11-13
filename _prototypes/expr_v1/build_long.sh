#!/bin/bash
# 試作ビルド（長尺）。Before＝今の表現／After＝表現コード v1。台本・声は同じ。アップロードしない。
set -e
C=$1; BEAT=$2; ANSWER=$3
B=_prototypes/expr_v1/before/$C; A=_prototypes/expr_v1/after/$C
python3 _tools/video/make_video.py $B/slide.html --out $B/video_build/out --speaker 11 --speed 1.1 --final-outro 3.0 --bgm _assets/audio/bgm_calm_loop.wav --sfx-dir _assets/audio
python3 _tools/video/make_video.py $A/slide.html --out $A/video_build/out --speaker 11 --speed 1.1 --final-outro 3.0 --lead 0.3 --intro 0.3 --expr v1 --num-gap 0.7 --beat "$BEAT" --answer-text "$ANSWER"
