---
name: yt-shorts-designer
description: Shorts制作の縦型スライドデザイナー役。1080x1920のセーフエリア・テロップ・STEPSを実装し、本編accent/キーイエローと整合させる。Use when building the vertical slide.html for a Shorts video. Triggers - Shorts縦型スライド, 9:16デザイン, セーフエリア調整
---

# Shortsスライドデザイナー（縦型実装）

実世界の対応役割：SNS用切り抜き編集者。
原則：**stage.html を手で書かない。`spec.py`（宣言的データ）だけを書き、
`gen_stage.py` で生成する**——エンジン部分（keyframes/rv-*/`.se`/`#__heartbeat`）を
壊しようがない構造にしてある。

## 入力
- yt-shorts-hookwriterの台本（shorts.md）

## 手順

1. `.claude/skills/episode-production/shorts-production.md` §3（縦型デザイン数値基準）を読む
2. `<episode_dir>/shorts_build/shortN/spec.py` を書く。**形式と要素種は
   `_tools/shorts_template/gen_stage.py` 冒頭のdocstringが正**。既存EPのspec.py
   （例: `02_intermediate/ep06_pricing-psychology/shorts_build/short1/spec.py`）を雛形にする
3. spec.py の必須整合:
   - `accent`/`glow` = 本編 slide.html の `:root { --accent:... }` と同値
   - `narrations` = shorts.md と**文字単位で一致**（verify_shortsが検査）
   - `els` は話す順に並べる（そのままSTEPSになる）
   - `caption` は1行15〜18字。表示は 文字数÷4秒 以上確保
   - S1の最初の要素は1秒以内に動きを出す（`t:0.0`）。中盤でanim種を1回変える
   - `k-line` は1行約9文字まで。長い文は `<br>` を意味の切れ目に入れる
     （1〜2文字のぶら下がりはverifyがFAILさせる）
4. 生成と検証（このペアを通るまでspec.pyを直す）:
   ```bash
   python3 _tools/shorts_template/gen_stage.py <dir>/spec.py <dir>/stage.html
   python3 _tools/checks/verify_shorts.py <dir>
   ```
5. spec.py と stage.html を**両方コミット**する

## verify_shortsの主なFAILとspec側の直し方

| FAIL | 直し方 |
|---|---|
| ナレーション不一致 | spec.narrations を shorts.md の「」内と一字一句合わせる（変えたい時はshorts.md側も直す） |
| 冒頭フック信号なし | shorts.md S1に数字/なぜ/〜ませんか等を入れ、spec側も追随 |
| ループ共通語なし | S1とS5のナレーションに同じ2文字以上の語（漢字/カタカナ/数字）を入れる |
| 行末ぶら下がり | `<br>` の位置を意味の切れ目に移す・文言を短くする |
| セーフエリア侵犯 | 要素を減らす・文字数を減らす（座標指定はテンプレ側なので通常起きない） |

## 完了条件
- [ ] verify_shorts.py が RESULT: PASS（9項目）
- [ ] spec.py / stage.html をコミット済み

## 引き継ぎ
→ **yt-shorts-video-editor**（`bash _tools/pipeline/run_shorts.sh <ep_dir>` でビルド）
