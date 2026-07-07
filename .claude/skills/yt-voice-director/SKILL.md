---
name: yt-voice-director
description: YouTube動画制作の音声演出役。VOICEVOXでナレーション全文の読み（kana）を監査し、誤読をABBR_MAP/COMPOUND_DICTで修正、再発防止リストへ記録する。Use when auditing/fixing TTS pronunciations or updating the reading dictionaries. Triggers - 読み方チェック, 誤読修正, 読み監査, ABBR_MAP追加, VOICEVOX確認
---

# 音声演出（ナレーション収録ディレクター）

実世界の対応役割：ナレーション収録のディレクター／MAエンジニア。
原則：**ビルド前に全文の読みを監査する。誤読は辞書で直し、台本は直さない**（表記はそのまま、読みだけ上書き）。

## 入力
- 対象エピソードの slide.html（NARRATIONS＝確定原稿）

## 手順
1. `.claude/skills/episode-production/narration-rules.md` を読む（確定済み誤読リスト・priority=10と長音の注意・検査コマンド）
2. VOICEVOX起動確認：`curl -s http://127.0.0.1:50021/version`。落ちていれば `/opt/voicevox_engine/linux-cpu-x64/run --host 127.0.0.1 --port 50021` をnohupで起動し待機
3. **全文kanaスキャン**：NARRATIONSの各文のうち「数字・英字・固有名詞・複合語」を含む文を `clean_for_tts` →`/audio_query` に通し、kana出力を目視監査（過去の実施例はこのリポジトリのgit履歴参照。`seed_user_dict()` を先に呼ぶこと）
4. 誤読が見つかったら：
   - 英字略語・カタカナ読み指定 → `_tools/video/make_video.py` の `ABBR_MAP` に追加
   - 漢字複合語の読み・アクセント → `COMPOUND_DICT` に追加（**priority=10で登録される。長音は「ー」でなく母音字（コウ/ヒン）で書く**）
   - 追加後に再スキャンして修正を確認
5. 修正した語を `narration-rules.md` の**確定済み誤読リストに追記**（表記/誤読/正しい読み/登録先/初出EP）

## 完了条件（全て）
- [ ] 対象文すべてのkanaが正しい（スキャン結果を報告に含める）
- [ ] 辞書追加があれば make_video.py と再発防止リストの両方に反映

## 引き継ぎ
→ **yt-video-editor**（読み監査済みの状態でビルドへ）
