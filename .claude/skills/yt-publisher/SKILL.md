---
name: yt-publisher
description: YouTube動画制作の配信担当役。概要欄SEO・サムネイル設計メモ・Shorts台本3本・公開時チェックリストを整備する。Use when preparing description/thumbnail/shorts or the publish checklist for an episode. Triggers - 概要欄作成, サムネ設計, Shorts台本, 公開準備, description更新
---

# パブリッシャー（配信・グロース担当）

実世界の対応役割：YouTubeチャンネル運用担当。
原則：**検索KWをタイトル・概要欄冒頭2行・チャプターの3か所で一致させる**（計画書§3-D）。

## 入力
- 完成した script.md（パッケージング表・タイムスタンプ）

## 手順
1. `.claude/skills/episode-production/retention-packaging.md` §5（SEO規則）・§6（Shorts）と `templates.md` の description テンプレを開く
2. **description.md**：冒頭2行にKW＋視聴メリット（「第N回」禁止）／サブKW入りチャプター／参考文献はscript.mdと一致／ハッシュタグ
   - **リードマグネットCTA（必須）**：メイン説明文の**フック直後（2段落目）**に無料チートシートの導線を入れる（リスト獲得＝収益化戦略§L3の入口）。定型：
     ```
     ▼【無料】マーケの型 全20話まとめ＆実践チートシート（PDF）を配布中
     👉 https://witty-composer-9473.kit.com/ac0f4ce77b
     ```
     （URLは `docs/mailing-list-plan.md` が正。変わったらそこと本行を更新）
3. **thumbnail.md**：パッケージング表のサムネ文字・約束と整合させる（背景 #0B1220 シリーズ共通、アクセントは slide.html の `--accent` と同色、A/B用の代替案を1つ以上）。
   **このファイルは機械可読**——`make_thumbnail.py` が「## メインテキスト…」の `**採用：**` 行（無ければ最初の太字）と「## サブテキスト…」の候補A行からPNGを自動生成する。確実に指定したい場合は `## サムネ生成データ` ブロックに `main:` / `sub:` を書く
4. **サムネPNG生成**：`python3 _tools/publish/make_thumbnail.py <ep_dir>` → `<ep_dir>/thumbnail.png`（1280x720・シリーズ共通デザイン・数字はアクセント色強調）。生成後にReadで目視確認し**コミットする**。アップロード時に upload_youtube.py が自動設定する
5. **shorts.md**：3本（S7リフック素材／ミニ問いかけ素材／まとめの1アクション。各15〜30秒・ナレーション合計150字以内（`shorts-production.md` §2 が正）、冒頭3秒に本編と同じアンカー、末尾に長編への橋渡し、KW型タイトル）
6. **公開時チェックリスト**を報告に添付（`pipeline.md` の「公開前の手動作業」が正。24話の Shorts の関連動画リンク／固定コメントのピン留め／エンドスクリーン・カード）。公開予約・AI音声の開示申告は自動なので、手動の項目に書かない

## 完了条件（全て）
- [ ] description.md・thumbnail.md・shorts.md が最新パッケージングと整合
- [ ] thumbnail.png を生成・目視確認・コミット済み
- [ ] KW表記がタイトル・冒頭2行・チャプターで一致（grepで確認）
- [ ] 公開時チェックリストを添付済み
- [ ] 概要欄・サムネの数字と固有名詞が、script.md の「## 数字の確認」の表・`docs/proper-nouns.md` と同じ（表に無い数字を概要欄で足さない）

## 引き継ぎ
→ ユーザー（YouTube Studio作業）／公開後 → **yt-analyst**
