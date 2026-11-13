#!/bin/bash
# 比較用の動画と画像を作る（_prototypes/expr_v1/compare/）。アップロードはしない。
set -e
P=_prototypes/expr_v1; O=$P/compare; mkdir -p $O
FONT=/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc
U=u01_jcpenney-sale; C=c01_jcpenney-fair-and-square
SB=$(ls $P/before/$U/shorts_build/short1/*_final.mp4); SA=$(ls $P/after/$U/shorts_build/short1/*_final.mp4); SV=$(ls $P/visual/$U/shorts_build/short1/*_final.mp4)
LB=$(ls $P/before/$C/video_build/out/*_final.mp4); LA=$(ls $P/after/$C/video_build/out/*_final.mp4)
lab(){ echo "drawbox=x=0:y=0:w=iw:h=$3:color=black@0.75:t=fill,drawtext=fontfile=$FONT:text='$1':fontcolor=white:fontsize=$2:x=(w-text_w)/2:y=($3-text_h)/2"; }
norm="fps=30,format=yuv420p"
# Short：1本ずつ（ラベルつき）と、3本を続けて流す版（それぞれの音で聞ける）
ffmpeg -v error -y -i $SB -vf "$(lab '① いまの表現（Before）' 44 110),$norm" -c:v libx264 -crf 20 -c:a aac -ar 48000 -ac 2 $O/s1.mp4
ffmpeg -v error -y -i $SA -vf "$(lab '② 表現コード v1・静止スライド版' 44 110),$norm" -c:v libx264 -crf 20 -c:a aac -ar 48000 -ac 2 $O/s2.mp4
ffmpeg -v error -y -i $SV -vf "$(lab '③ 表現コード v1・素材組み込み版' 44 110),$norm" -c:v libx264 -crf 20 -c:a aac -ar 48000 -ac 2 $O/s3.mp4
printf "file 's1.mp4'\nfile 's2.mp4'\nfile 's3.mp4'\n" > $O/s.txt
ffmpeg -v error -y -f concat -safe 0 -i $O/s.txt -c copy $O/比較_Short_u01_①今→②v1静止→③v1素材.mp4
# Short：3本を横に並べた版（絵の比較用。音は③）
ffmpeg -v error -y -i $O/s1.mp4 -i $O/s2.mp4 -i $O/s3.mp4 -filter_complex "[0:v]scale=540:960[a];[1:v]scale=540:960[b];[2:v]scale=540:960[c];[a][b][c]hstack=inputs=3[v]" -map "[v]" -map 2:a -c:v libx264 -crf 20 -c:a aac -shortest $O/比較_Short_u01_横並び（音は③）.mp4
# 長尺：1本ずつ（ラベルつき）と、冒頭60秒を続けて流す版
ffmpeg -v error -y -i $LB -vf "$(lab 'いまの表現（Before）' 40 80),$norm" -c:v libx264 -crf 21 -c:a aac -ar 48000 -ac 2 $O/比較_長尺_c01_Before.mp4
ffmpeg -v error -y -i $LA -vf "$(lab '表現コード v1（After）' 40 80),$norm" -c:v libx264 -crf 21 -c:a aac -ar 48000 -ac 2 $O/比較_長尺_c01_After.mp4
ffmpeg -v error -y -t 60 -i $O/比較_長尺_c01_Before.mp4 -c copy $O/l1.mp4; ffmpeg -v error -y -t 60 -i $O/比較_長尺_c01_After.mp4 -c copy $O/l2.mp4
printf "file 'l1.mp4'\nfile 'l2.mp4'\n" > $O/l.txt
ffmpeg -v error -y -f concat -safe 0 -i $O/l.txt -c copy $O/比較_長尺_c01_冒頭60秒_Before→After.mp4
rm -f $O/s?.mp4 $O/l?.mp4 $O/*.txt
ls -la $O
