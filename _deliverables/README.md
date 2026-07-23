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

- CTAリンクは環境変数で差し込む：`LEAD_CHANNEL_URL` / `LEAD_NEXT_URL` / `LEAD_CONTACT_URL`
- **公開動画と文言を一致させたい場合は、script.md が正となるブランチで実行**すること
  （ブランチにより台本内容が異なりうる。真実源は各話の実制作ブランチ）。
- PDF化する場合は任意のMarkdown→PDF変換で（本ツールはMarkdownまで生成）。

## 今後追加予定（戦略書のオフYouTube施策）

- `note/` — 各script.md → note記事（第二の検索戦線・§5-2）
- `affiliate/` — 各EPの参考書籍・ツールのアフィリエイトブロック（§L2）
- `course/` — Udemy/Brain講座の構成案（§L3・M3）
