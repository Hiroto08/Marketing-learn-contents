---
name: yt-video-editor
description: YouTube動画制作の映像編集役。make_video.pyでのビルド実行、映像/音声トラック長の一致検証、実測タイムスタンプでのscript/description修正、mp4納品まで行う。Use when building the episode video, verifying A/V sync, or fixing timestamps after build. Triggers - 動画化して, ビルドして, 再録画, タイムスタンプ修正, mp4作成
---

# 映像編集（エディター・レンダリング）

実世界の対応役割：映像編集者・レンダリング担当。
原則：**ユーザーが明示的に動画化を指示した時だけビルドする。納品前にA/V一致を必ず検証**。

## 入力
- 読み監査済みの slide.html（yt-voice-director通過後）

## 手順
1. VOICEVOX起動確認（yt-voice-director §2と同じ）。ビルドは重いので**バックグラウンド実行**し、Monitorで完了を待つ
2. ビルド（シリーズ標準パラメータ）：
   ```bash
   python3 _tools/video/make_video.py <episode_dir>/slide.html \
     --out <episode_dir>/video_build/out --speaker 11 --speed 1.1 --final-outro 3.0
   ```
3. **A/V検証**：final.mp4 の video/audio トラック長を ffprobe で取得し **差±0.1秒以内** を確認（過去にChromiumの静止画面でフレーム記録が止まり音声より映像が短くなる不具合があった。tpad対策済みだが検証は必須）。1秒超のずれがあるスライドは `.work/slides/slide_NN.mp4` 単位で特定し `--slide N` で再録画
4. **タイムスタンプ実測修正**：`.claude/skills/episode-production/SKILL.md` の「動画ビルド後のタイムスタンプ修正」手順で実測値を出し、script.md の全スライド見出しと description.md のタイムスタンプ/チャプター生成用を更新
5. mp4はコミットしない（`**/video_build/*.mp4` はgitignore済み）。タイムスタンプ修正だけコミット対象
6. SendUserFileでmp4を納品（尺・A/V差・修正済みタイムスタンプを添えて）

## 完了条件（全て）
- [ ] final.mp4生成・A/V差±0.1秒以内（数値を報告）
- [ ] script.md / description.md のタイムスタンプが実測値
- [ ] mp4をユーザーへ送付済み

## 引き継ぎ
→ **yt-publisher**（公開チェックリストの添付）／公開後 → **yt-analyst**
