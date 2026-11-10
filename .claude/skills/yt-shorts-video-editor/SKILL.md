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

- spec→stage生成、verify_shorts、読み検査（ビルド前）、数字の確認、AI臭さ検査、縦型ビルド（--speed 1.15・詰めパディング）、
  A/V差≤0.1s・尺15〜30s・全スライドvideo+audioストリーム検査、読み検査（ビルド後の音声の照合）、実施記録（quality_record.md）まで**全部この1コマンド**
- テロップを出す時刻は自動で決まる：テロップ同期型（第2シリーズ）は文を読み始める0.15秒前、24話の Shorts は1.2秒前（run_shorts.sh が stage.html を見て切り替える）
- 1本あたり2〜4分。複数本はバックグラウンド実行で待つ
- FAILの対処は `.claude/skills/episode-production/pipeline.md` のプレイブック参照

## 個別ビルド（部分再実行したい時）

```bash
python3 _tools/video/make_video.py <dir>/stage.html \
  --out <dir> --speaker 11 --speed 1.15 \
  --lead 1.2 --intro 0.3 --outro 0.5 --final-outro 1.2 \
  # ↑ 第2シリーズ（テロップ同期型）は --lead 0.15
  --width 1080 --height 1920 \
  --bgm _assets/audio/bgm_calm_loop.wav --sfx-dir _assets/audio
```

※0フレーム録画（負荷時にChromiumのscreencastが間欠的に起こす）はエンジンが最大3回自動再録画する。
それでも欠落が残る場合のみ該当slide_NN.mp4を削除して`--slide N`で手動再録画し、
stage.htmlに`#__heartbeat`が残っているか確認（specから生成していれば必ず残る）。

## 完了条件
- [ ] run_shorts.sh が `SHORTS PIPELINE PASS`（各本の尺・A/V差を報告）
- [ ] `quality_record.md` の末尾が「機械検査の結果：PASS」。コミットする（`built_readings.json` も）
- [ ] 最初・中盤・最後のフレームを切り出し、画面の文字が spec.py の改行どおりであることを確かめる（録画の使い回しで古い文字が残っていないか）
- [ ] 第2シリーズ：mp4 がレビュー便（Drive）に送られている（upload_youtube.py が自動で送る）
- [ ] mp4は`shorts_build/`配下に保存（gitignore対象。コミットしない）

## 引き継ぎ
→ **yt-shorts-qa**（最終検品）→ **yt-uploader**（run_shorts.sh --upload なら完了済み）
