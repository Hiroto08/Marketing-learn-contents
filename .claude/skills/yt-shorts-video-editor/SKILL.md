---
name: yt-shorts-video-editor
description: Shorts制作の映像編集役。縦型1080x1920でのビルド実行、A/V検証、ループ接続の目視確認を行う。Use when building/rendering a Shorts video. Triggers - Shorts動画化, 縦型ビルド, Shortsレンダリング
---

# Shorts映像編集（縦型ビルド）

実世界の対応役割：ショート動画のレンダリング担当。
原則：**本編と同じ検証基準（A/V一致・ラウドネス）＋Shorts固有の項目（尺・ループ）を追加で確認**。

## 入力
- yt-shorts-designerの縦型slide.html（stage.html）

## 手順
1. `.claude/skills/episode-production/shorts-production.md` §5 のビルドコマンドを実行：
   ```bash
   python3 _tools/video/make_video.py <stage.html> \
     --out <episode_dir>/shorts_build/shortN \
     --speaker 11 --speed 1.15 --final-outro 1.0 \
     --width 1080 --height 1920 \
     --bgm _assets/audio/bgm_calm_loop.wav --sfx-dir _assets/audio
   ```
2. **A/V検証**：final.mp4のvideo/audioトラック長を確認（差±0.1秒以内）。**全スライド（特にS1相当）にvideoストリームが存在することを個別に確認**する（`ffprobe -show_entries stream=codec_type`。videoストリームが1本でも欠落していたら、該当slide_NN.mp4を削除して該当スライドのみ`--slide N`で再録画——テンプレートの`#__heartbeat`が正しく効いているか併せて確認）
3. ラウドネス確認（-14 LUFS前後、本編と同じ基準）
4. ループ接続の目視確認：最初と最後の数秒を切り出して連続再生し、違和感なくループするか確認
5. mp4は`shorts_build/`配下に保存（gitignore対象。コミットしない）

## 完了条件
- [ ] A/V差±0.1秒以内
- [ ] 全スライドにvideo+audioストリームが存在（欠落なし）
- [ ] 尺30〜45秒
- [ ] ループ接続を目視確認済み

## 引き継ぎ
→ **yt-shorts-qa**（最終検品）
