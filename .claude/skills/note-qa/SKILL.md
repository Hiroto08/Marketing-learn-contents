---
name: note-qa
description: note記事の品質管理・検品。verify_note.py を独立再実行し、公開前チェックリスト（読み物性・動画整合・入口・導線）で最終判定する。他ロールの成果物を独立に再検証する最後のゲート。Use when reviewing/verifying a finished note article before commit or publish.
when_to_use: "Triggers: note検品, note QA, note最終チェック, noteレビュー, note校了判定"
---

# note 検品（QA・最終ゲート）

実世界の対応役割：編集部の**校了担当**。書いた本人以外が独立に確認する最後の関門。
原則：**他ロールの「できた」を信用せず、自分で機械検査を再実行して確かめる。** RESULT: PASS が出るまで校了しない。

## 入力
- 校正まで終えた `_deliverables/note/ep<NN>_*.md`

## 手順
1. **機械検査を独立再実行**（これが一次の合否）：
   ```bash
   python3 _tools/checks/verify_note.py _deliverables/note/ep<NN>_*.md
   ```
   RESULT: FAIL の項目は該当ロールへ差し戻す（禁止語→note-writer、タイトル長→note-packager 等）
2. **人手チェックリスト**（機械化できない品質。全て満たすまでPASSにしない）：
   - [ ] **読み物性**：冒頭3段落で読み進めたくなるか。話し言葉のダレが残っていないか
   - [ ] **1テーマ**：詰め込みすぎず、1本で1つの学びに絞れているか
   - [ ] **動画整合**：数字・固有名詞・主張が動画と矛盾しないか（抜き取り3点を script.md と照合）
   - [ ] **入口**：タイトルが検索KWを含み、得/損/数字が主語か
   - [ ] **導線**：CTAが 動画→チャンネル→特典 の順で、リンクが壊れていないか
   - [ ] **見出し画像案**：コンセプトメモがあるか
3. 全て満たしたら **RESULT: PASS** を明記して監督へ返す。1つでも欠ければ差し戻し先を明示

## やってはいけないこと
- verify_note.py を自作・改変して通す（検査の信頼が壊れる）
- 機械検査PASSだけで校了（人手チェックリストの主観品質は別途必須）

## 完了条件（全て）
- [ ] verify_note.py が RESULT: PASS
- [ ] 人手チェックリスト全項目を確認済み
- [ ] PASS/FAIL と（FAILなら）差し戻し先を報告

## 引き継ぎ
→ **note-production**（監督がコミット）／不合格なら該当ロールへ差し戻し
