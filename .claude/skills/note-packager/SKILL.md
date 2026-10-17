---
name: note-packager
description: note記事のパッケージ編集。クリックされるタイトル・見出し画像コンセプト・ハッシュタグ・目次・検索KW・CTA導線を設計する。noteの発見（検索/おすすめ/Google）に効く「入口」を担う。Use when setting a note article's title, tags, header-image concept, or CTA.
when_to_use: "Triggers: noteタイトル, note見出し画像, noteハッシュタグ, noteパッケージ, note目次, noteSEO"
---

# note パッケージ編集（入口設計）

実世界の対応役割：編集部の**タイトル/SEO担当・アートディレクション窓口**。
原則：**中身が良くても入口が弱いと読まれない。** noteの流入は「note内検索・おすすめ・Google・SNS」。タイトルとハッシュタグと見出し画像で決まる。

## 入力
- リライト済みの `_deliverables/note/ep<NN>_*.md`
- 対応 `<ep_dir>/description.md`（検索KW・サムネ文言の流用元）

## 手順
1. **タイトル（H1）を確定**：note推奨は全角32字前後。以下を満たす
   - 読者の得・損・数字が主語（フレームワーク名は【】内か後半）
   - 検索KW（例「STP分析 やり方」「ペルソナ 作り方」）を前方に自然に含める
   - 動画タイトルと完全一致でなくてよい（noteはnoteの検索意図に最適化）
   - 3案作って最良を選ぶ（残り2案は本文末にコメントアウトで残さず、監督へ口頭提示）
2. **見出し画像コンセプト＋画像生成**：note記事は見出し画像で一覧クリック率が変わる。文字6〜9字＋数字1つ＋シリーズ共通色の**設計メモ**を記事末尾に `<!-- 見出し画像案: メイン「…」／サブ「…」／数字 …／背景 シリーズ共通色 #0B1220 -->` の形で残す。**メモを書いたら必ず画像PNGも生成して貯める**：
   ```bash
   python3 _tools/publish/make_note_thumbnail.py --file _deliverables/note/ep<NN>_*.md
   ```
   → `_deliverables/note/thumbnails/ep<NN>.png`（1280x670・コミット対象）。メイン/サブはメモから自動抽出、アクセント色は本編slide.htmlから自動取得。生成後は目視で文字切れ・数字強調を確認。noteへの画像添付は非公式API範囲外＝生成PNGは人がnote編集画面で設定する
3. **目次**：`##` 見出しが読者導線として機能するか確認。多すぎ（20超）は統合、羅列は言い換え
4. **ハッシュタグ**：3〜8個。note内で回遊される粒度の大きいタグ（#マーケティング #マーケティング入門）＋その回固有のKWタグ（#STP分析 等）を混ぜる
5. **CTA導線の確認**：`## この記事は動画でも見られます` ブロックが
   - 動画URL（`docs/upload-status.md`由来）→ チャンネル → **無料特典（リードマグネット）の順**
   - **特典＝チートシートのオプトインURL**（`make_note_article.py` の `DEFAULT_NEXT` に設定済み＝自動反映）。
     現行URLは `https://witty-composer-9473.kit.com/ac0f4ce77b`（`docs/mailing-list-plan.md`が正）。手編集で消さない
6. **冒頭の検索KW配置**：リード1〜2段落目に検索KWを1回自然に入れる（note内検索/Google対策）

## 完了条件（全て）
- [ ] タイトルが32字前後・検索KWを前方に含む（3案から選定）
- [ ] ハッシュタグ3〜8個（大タグ＋固有KWタグ）
- [ ] 見出し画像コンセプトのメモが入っている＋ `_deliverables/note/thumbnails/ep<NN>.png` を生成・コミット
- [ ] CTAが 動画→チャンネル→特典 の順で導線として成立

## 引き継ぎ
→ **note-proofreader**（校正・校閲）
