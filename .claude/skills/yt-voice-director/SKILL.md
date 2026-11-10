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
1. `.claude/skills/episode-production/quality-gates.md` §1（R1〜R10）と `narration-rules.md` の「確定済み誤読リスト」を読む
2. VOICEVOX 起動確認：`curl -s http://127.0.0.1:50021/version`。落ちていれば `bash _tools/setup_env.sh`（これ以外の起動方法は使わない）
3. **読み検査（機械）**：
   ```bash
   python3 _tools/checks/check_readings.py <ep_dir> --main --review     # 本編・ケースファイル
   python3 _tools/checks/check_readings.py <ep_dir>/shorts_build/shortN  # Short 1本
   ```
   - R1 固有名詞が台帳に無い → yt-researcher に戻す（読みを一次ソースで確かめて台帳へ）。確認できない名前は脚本家に戻して消す
   - R3 人名が辞書に無い → `_tools/video/make_video.py` の `COMPOUND_DICT` に登録（**長音は「ー」でなく母音字（コウ/ヒン）で書く**。アクセント型は narration-rules.md）
   - R4・R5・R8 読みが違う・途中で切れる → `COMPOUND_DICT`（複合語・人名）／`ABBR_MAP`（英字）／`READING_MAP`（辞書で直らない読みを、合成の直前にかなへ開く）で直す。**画面の文字は変えない**
   - R7 英字の読みが未定 → `ABBR_MAP` に登録
   - R10 別の辞書と読みが食い違う → 1語ずつ読みを確かめる。VOICEVOX が正しければ `_tools/checks/reading_confirmed.txt` に「表記・読み・確かめた根拠」を足す。間違っていれば辞書で直す
4. `<ep_dir>/reading_review.txt`（全文の読み。★＝固有名詞を含む行）を上から読み、★の行の読みが台帳と同じことを確かめる
5. 新しい誤読を直したら、3か所に書く：辞書（make_video.py）／`check_readings.py` の `BAD`（型）／`narration-rules.md` の確定済み誤読リスト（表記・誤読・正しい読み・登録先・初出）
6. **ビルド後の照合**（yt-video-editor がビルドした後）：`python3 _tools/checks/check_readings.py <dir> --built` が PASS（R9：実際に音声になった読みが、今の原稿・台帳と一致）。run_episode.sh／run_shorts.sh は自動で実行する

## 完了条件（全て）
- [ ] `check_readings.py` が RESULT: PASS（ビルド前。R1〜R8・R10）
- [ ] ビルド後に `check_readings.py --built` が RESULT: PASS（R9）
- [ ] 辞書を足したときは、make_video.py・BAD・narration-rules.md の3か所に反映
- [ ] 抑揚・間（V1〜V4）は判定しない（AI は音声を聞けない。レビュー便で聞いた人が `quality_record.md` に記入する）

## 引き継ぎ
→ **yt-video-editor**（読み監査済みの状態でビルドへ）
