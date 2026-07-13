---
name: yt-video-editor
description: YouTube動画制作の映像編集役。make_video.pyでのビルド実行、映像/音声トラック長の一致検証、実測タイムスタンプでのscript/description修正、mp4納品まで行う。Use when building the episode video, verifying A/V sync, or fixing timestamps after build. Triggers - 動画化して, ビルドして, 再録画, タイムスタンプ修正, mp4作成
---

# 映像編集（エディター・レンダリング）

実世界の対応役割：映像編集者・レンダリング担当。
原則：**ユーザーが明示的に動画化を指示した時だけビルドする。ゲートは機械検査（postbuild_episode.py）に任せ、独自の品質判断をしない**。

## 標準手順（これだけでよい）

```bash
bash _tools/pipeline/run_episode.sh <episode_dir>            # ビルド〜検証〜サムネまで
bash _tools/pipeline/run_episode.sh <episode_dir> --upload   # アップロードまで（yt-uploader工程込み）
```

- VOICEVOX起動確認・verify_episode・BGM/SFXミックスビルド・A/V検証・LUFS・
  タイムスタンプ実測修正・mp4ステージング・サムネ生成まで**全部この1コマンドに入っている**
- ビルドは重い（30分前後）ので**バックグラウンド実行**し、Monitor/通知で完了を待つ
- FAILしたら出力の指示に従う（対処表: `.claude/skills/episode-production/pipeline.md` のプレイブック）

## 個別に実行したい時（部分再実行）

```bash
# ビルドのみ（シリーズ標準＝BGM・SFXミックス込み。仕様: episode-production/audio-production.md）
python3 _tools/video/make_video.py <episode_dir>/slide.html \
  --out <episode_dir>/video_build/out --speaker 11 --speed 1.1 --final-outro 3.0 \
  --bgm _assets/audio/bgm_calm_loop.wav --sfx-dir _assets/audio

# 後処理のみ（A/V判定・LUFS -16〜-13・タイムスタンプ実測修正・ステージング）
python3 _tools/video/postbuild_episode.py <episode_dir>

# 特定スライドの再録画（postbuildが「単体超過」を出した時だけ）
# → 指示された slide_NN.mp4 を消して make_video.py に --slide N を付けて再実行
```

A/V合格基準（postbuildに実装済み・変更しない）: 合計差≤0.2秒 かつ 全スライド単体≤0.1秒。
1/25秒フレーム量子化の蓄積で合計0.1〜0.2秒になるのは正常（EP01/02実測で確認済み）。

## 完了条件（全て）
- [ ] postbuild_episode.py が `POSTBUILD PASS`（A/V・LUFSの数値を報告）
- [ ] script.md / description.md のタイムスタンプが実測値（postbuildが自動更新。コミットする）
- [ ] mp4をSendUserFileでユーザーへ送付済み（尺・A/V差を添えて）
- [ ] mp4はコミットしない（gitignore済み）

## 引き継ぎ
→ **yt-uploader**（run_episode.sh --upload なら完了済み）／公開後 → **yt-analyst**
