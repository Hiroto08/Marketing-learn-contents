# _deliverables — オフYouTubeのマネタイズ配布物

YouTube以外の収益化導線（リスト獲得・外部流入・教材）で使う配布物と、その生成物置き場。
YouTube本体（動画・概要欄・アップロード）は別セッション／別領域が担当し、ここには**触れない**。

## lead-magnet/ — 全話まとめ＆実践チートシート

- 生成物：`marketing-lab-cheatsheet.md`（メール/LINE登録の特典＝リードマグネット。戦略書 §3-L3）
- 生成ツール：`_tools/repurpose/make_lead_magnet.py`
- 原料：各EPの `script.md`（学習ゴール＋原則/適用スライドの見出し）

### 更新方法

```bash
python3 _tools/repurpose/make_lead_magnet.py \
  --out _deliverables/lead-magnet/marketing-lab-cheatsheet.md
```

- CTAリンクは環境変数で差し込む：`LEAD_CHANNEL_URL`（既定=実チャンネル）/ `LEAD_NEXT_URL`（特典/登録URL）/ `LEAD_CONTACT_URL`
- **公開動画と文言を一致させたい場合は、script.md が正となるブランチで実行**すること（真実源は各話の実制作ブランチ）
- 配布形態：**note限定公開URL**が最速（ホスティング不要）。PDF化する場合は任意のMarkdown→PDF変換で

## note/ — note記事（第二の検索戦線・§5-2）

- 生成：`_tools/repurpose/make_note_article.py`（各script.mdのナレーション→読み物）
- 編集：`note-*` ロールスキル＋機械検査 `_tools/checks/verify_note.py`
- 下書き自動保存：`_tools/publish/post_note_api.py`（このコンテナで動くrequests版）／`post_note.py`（ローカルPC用Playwright版）

## list/ — メール/LINEリストの文面資産（§L3・`docs/mailing-list-plan.md`）

- `opt-in-lp.md` … オプトインLP/フォームのコピー（メールサービスに貼る）
- `welcome-email.md` … 登録直後の自動返信#1（チートシート納品）
- `kit-setup.md` … Kitの貼り付けシート（確認メール方式・確定版）
- 進め方の全体像は `docs/mailing-list-plan.md`

## broadcast/ — 週次ブロードキャストメール草稿（定常配信・EP07開始）

- 生成：`_tools/repurpose/make_broadcast.py --episode <ep_dir>`（script.md→短いダイジェスト）
- 役割：`list-broadcast` スキル。**送信はKit → Broadcasts で人間が最終確認して送る**

## 今後追加予定

- `affiliate/` — 各EPの参考書籍・ツールのアフィリエイトブロック（§L2）
- `course/` — Udemy/Brain講座の構成案（§L3・M3）
