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

- **チャンネルURLは実チャンネルを既定値**に設定済み（`LEAD_CHANNEL_URL`で上書き可）
- `LEAD_NEXT_URL`（特典）/`LEAD_CONTACT_URL`（問い合わせ）は**未設定なら該当行を出さない**
  （チートシートをどこかにホストしたらURLを渡す。空プレースホルダは出力しない）
- **公開動画と文言を一致させたい場合は、script.md が正となるブランチで実行**すること
  （ブランチにより台本内容が異なりうる。真実源は各話の実制作ブランチ）。
- PDF化する場合は任意のMarkdown→PDF変換で（本ツールはMarkdownまで生成）。

## note/ — note記事（第二の検索戦線・§5-2）

- 生成物：`ep<NN>_<slug>.md`（各EPのナレーションを読み物に再構成。末尾に動画・特典CTA＋ハッシュタグ）
- 生成ツール：`_tools/repurpose/make_note_article.py`
- 原料：各EPの `script.md` の **ナレーション：** ブロック（制作用タグ・アニメ指示は除外）

```bash
python3 _tools/repurpose/make_note_article.py --all          # 実スクリプトのある全話
python3 _tools/repurpose/make_note_article.py --episode <ep_dir>
```

- チャンネルURLは実チャンネルを既定値に設定済み（`LEAD_CHANNEL_URL`で上書き可）
- **動画URLは `docs/upload-status.md` があれば各話のvideoIdから自動解決**（無ければ該当行を出さない。
  `NOTE_VIDEO_URL`で単一上書きも可）。canonicalブランチで実行すれば全話に動画リンクが入る
- `LEAD_NEXT_URL`（特典）未設定時はソフト文言（「プロフィールのリンクから」）で出す
- 公開前に軽く目視推敲を推奨（AIナレーションは口語のため、note向けに接続を整えると尚良い）

## 今後追加予定（戦略書のオフYouTube施策）

- `affiliate/` — 各EPの参考書籍・ツールのアフィリエイトブロック（§L2）
- `course/` — Udemy/Brain講座の構成案（§L3・M3）
