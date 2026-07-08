---
name: yt-shorts-clipper
description: Shorts制作の切り出し企画役。完成した長編から3〜5本のShorts論点を選定し、各本の素材（本編セリフ・数字・図解）を特定する。Use when selecting which moments of a finished episode to cut into Shorts. Triggers - Shorts企画, 切り出し選定, どこを切り出す
---

# Shorts切り出し企画（プロデューサーのShorts版）

実世界の対応役割：番組から予告編/ハイライトを選ぶ編成担当。
原則：**Shortsは長編への送客装置ではなく発見装置**（`shorts-production.md` §1）。1本1メッセージ厳守。

## 入力
- 完成した script.md（本編。S7リフック・ミニ問いかけ・まとめの1アクション・固有図解の位置を把握する）

## 手順
1. `.claude/skills/episode-production/shorts-production.md` §1を読む（Shortsの位置づけ）
2. 本編から3〜5個の論点を選ぶ。優先候補：
   - S7（リフック①：意外な数字・反転）
   - S8-11のミニ問いかけ
   - S16-17（まとめの1アクション）
   - エピソード固有図解（S9等）
3. 各論点について、その論点だけで**単独で意味が通る**か確認する（前後の文脈が無いと理解できない論点は不採用）
4. 各論点に対して：使う本編ナレーション文・数字・キーワードを列挙し、フック候補（数字/断言/否定形/問いかけのいずれか）を1つ選ぶ
5. 3〜5本のリストを `<episode_dir>/shorts_plan.md` に書く（論点・使用素材・フック型・想定タイトル）

## 完了条件
- [ ] 3〜5本の切り出し案（各1論点・単独で理解可能）
- [ ] 各案にフック型（数字/断言/否定形/問いかけ）を明記

## 引き継ぎ
→ **yt-shorts-hookwriter**（切り出し案を渡す）
