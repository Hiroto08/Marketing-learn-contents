---
name: yt-shorts-video-editor
description: Shorts制作の映像編集役。縦型1080x1920でのビルド実行、A/V検証、ループ接続の目視確認を行う。Use when building/rendering a Shorts video. Triggers - Shorts動画化, 縦型ビルド, Shortsレンダリング
---

# Shorts映像編集（縦型ビルド）

実世界の対応役割：ショート動画のレンダリング担当。
原則：**本編と同じ検証基準（A/V一致・ラウドネス）＋Shorts固有の項目（尺・ストリーム欠落）を機械検査で確認**。

## 入力
- `<episode_dir>/shorts_build/shortN/spec.py`（yt-shorts-designerの成果物・コミット済み）

## 標準手順（これだけでよい）

```bash
bash _tools/pipeline/run_shorts.sh <episode_dir>            # 全Short: 生成→QA→ビルド→A/V検証
bash _tools/pipeline/run_shorts.sh <episode_dir> --upload   # アップロードまで（クォータ: 1日6本）
```

- spec→stage生成、verify_shorts（9項目）、縦型ビルド（--speed 1.15・詰めパディング）、
  A/V差≤0.1s・尺15〜30s・全スライドvideo+audioストリーム検査まで**全部この1コマンド**
- 1本あたり2〜4分。複数本はバックグラウンド実行で待つ
- FAILの対処は `.claude/skills/episode-production/pipeline.md` のプレイブック参照

## 個別ビルド（部分再実行したい時）

```bash
python3 _tools/video/make_video.py <dir>/stage.html \
  --out <dir> --speaker 11 --speed 1.15 \
  --lead 1.2 --intro 0.3 --outro 0.5 --final-outro 1.2 \
  --width 1080 --height 1920 \
  --bgm _assets/audio/bgm_calm_loop.wav --sfx-dir _assets/audio
```

※0フレーム録画（負荷時にChromiumのscreencastが間欠的に起こす）はエンジンが最大3回自動再録画する。
それでも欠落が残る場合のみ該当slide_NN.mp4を削除して`--slide N`で手動再録画し、
stage.htmlに`#__heartbeat`が残っているか確認（specから生成していれば必ず残る）。

## 完了条件
- [ ] run_shorts.sh が `SHORTS PIPELINE PASS`（各本の尺・A/V差を報告）
- [ ] ループ接続の目視確認（最初と最後の数秒を切り出して連続再生）
- [ ] mp4は`shorts_build/`配下に保存（gitignore対象。コミットしない）

## 引き継ぎ
→ **yt-shorts-qa**（最終検品）→ **yt-uploader**（run_shorts.sh --upload なら完了済み）
