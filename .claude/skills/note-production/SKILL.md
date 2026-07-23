---
name: note-production
description: 「AI時代のマーケティング・ラボ」のnote記事を、動画台本から公開品質へ仕上げる編集デスクの監督。make_note_article.py の下書きを起点に、note編集現場の4ロール（リライト→パッケージ→校正校閲→検品）を順に回して1本を校了させる。Use when creating, polishing, or finalizing a note article for an episode.
when_to_use: "Triggers: EPNNのnote記事を作って, note記事を仕上げて, note下書きをリライト, note公開準備, note校了"
---

# note編集デスク（監督）

実世界の対応役割：オウンドメディアの**編集長／デスク**。個々の執筆・校正はロールに委ね、監督は「角度の決定・進行・校了判定」を担う。
原則：**下書きは機械生成（make_note_article.py）で用意し、人手ロールが読み物に引き上げる。校了は verify_note.py の RESULT: PASS が唯一の合否**。感覚的な「良くなった」で公開しない。

## 制作体制：note編集の4ロール（本スキルが順に実行）

| # | ロール | スキル | 担当 | 主な成果物 |
|---|--------|--------|------|-----------|
| 1 | リライター | `note-writer` | 口語→読み物・リード・接続・YouTube語の除去 | 本文リライト |
| 2 | パッケージ編集 | `note-packager` | タイトル・見出し画像案・目次・ハッシュタグ・検索KW・CTA | 見出し周り／メタ |
| 3 | 校正・校閲 | `note-proofreader` | 誤字脱字・表記ゆれ・事実/数字/固有名詞の動画整合 | 校正済み本文 |
| 4 | 検品（QA） | `note-qa` | verify_note.py 独立再実行＋公開前チェックリスト（最終ゲート） | PASS/FAILレポート |

**実行順序**：0（下書き生成）→ 1 → 2 → 3 → 4（PASS後にコミット）。
個別依頼（「タイトルだけ」「校正だけ」）は該当ロールを単独起動してよい。

## 手順

0. **下書き生成**：正典スクリプトのあるブランチで
   ```bash
   python3 _tools/repurpose/make_note_article.py --episode <ep_dir>
   ```
   → `_deliverables/note/ep<NN>_<slug>.md`。**動画URLは docs/upload-status.md から自動解決**されるため、
   このファイルが最新のブランチで実行すること（さもないと動画リンクが入らない）。
1. **角度の決定（監督）**：この記事の読者は誰で、何を持ち帰るか。動画の要点のうち「文章で読む価値が高い1点」を主眼に据える（動画の丸写しにしない）。
2. `note-writer` → `note-packager` → `note-proofreader` を順に実行。各ロールの完了条件を満たさないまま次へ進まない。
3. `note-qa` を実行し `python3 _tools/checks/verify_note.py <file>` が **RESULT: PASS**。
4. PASS後にコミット（`_deliverables/note/` のみ。下書きの再生成で上書きしないよう、以後の編集は生成物への直接編集で行う）。
5. **note下書き自動保存（任意・要 note 認証）**：`docs/monetization-strategy.md` の「非公開投稿」原則に沿い、校了記事を note に**下書き（非公開）**として保存する。**公開は人間**。
   ```bash
   python3 _tools/publish/post_note.py --file _deliverables/note/ep<NN>_*.md --screenshot /tmp/note.png
   ```
   - 認証：`NOTE_COOKIE`（推奨）または `NOTE_EMAIL`/`NOTE_PASSWORD` をSecretsに
   - **必ず `--dry-run` でパースを確認してから実行**。初回・note UI変更時は `--headful --screenshot` で挙動確認し、壊れたら post_note.py の `SEL`（セレクタ）を調整
   - noteに公式APIは無く**UI操作のため壊れやすい**。verify_note.py PASS を前提に、下書き保存の成否は必ずスクショで確認

## 実行原則（最重要）

1. **検査は1コマンド**：`python3 _tools/checks/verify_note.py <file>` が唯一の合否。PASSまで校了と言わない
2. **動画と矛盾させない**：数字・固有名詞・主張は動画（script.md）と一致。記事で新しい事実を足すなら出典を確認
3. **YouTube語を残さない**：「この動画では」「スライド」「さっそく始めましょう」「チャンネル登録」等は本文から除去（CTAブロックを除く）
4. **生成物＝下書き、編集後が正**：一度リライトした記事を make_note_article.py で再生成して上書きしない（編集が消える）
5. **1記事＝1テーマ**：note読者は検索/回遊で来る。詰め込みすぎない

## 完了条件（全て）
- [ ] 4ロールを通過（各完了条件を満たす）
- [ ] verify_note.py が RESULT: PASS
- [ ] `_deliverables/note/ep<NN>_*.md` をコミット

## 引き継ぎ
→ ユーザー（note.comへ貼り付け・見出し画像設定・公開）。公開後の反応は収益化戦略§5-2の第二戦線として観測。
