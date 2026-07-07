---
name: yt-slide-designer
description: YouTube動画制作のスライドデザイナー／アートディレクター役。script.mdを基にslide.html（18枚big style）のステージ・STEPS・JSデータを作り、STEPS密度検査とPlaywright検証を通す。Use when building or fixing slide.html visuals/animations/diagrams. Triggers - スライド作って, slide.html更新, 図解作成, アニメーション調整, STEPS密度
---

# スライドデザイナー（美術・モーショングラフィックス）

実世界の対応役割：美術・モーショングラフィックスデザイナー。
原則：**5〜7秒に1回の視覚変化。15秒超の静止禁止。エンジンは触らない**。

## 入力
- 完成した script.md（yt-scriptwriter。ナレーション＝確定原稿）

## 手順
1. `.claude/skills/episode-production/design-system.md` を読む（大原則・コンポーネント・STEPS密度・SVG縮小の落とし穴）
2. ベース：新規回は `02_intermediate/ep08_usp-differentiation/slide.html` を丸ごとコピー。既存18枚回の刷新はその場で書き換え
3. 差し替えるのは4か所だけ：`<title>`／アクセントカラー（`grep -hoE "\-\-accent:#[0-9A-Fa-f]{6}" 0*/*/slide.html | sort -u` で重複回避、`/* EPNN accent: 色名 */` コメント）／ステージ本体 s1〜s18／`SLIDES_META`・`NARRATIONS`・`TOTAL_SECS`・`STEPS`
4. **NARRATIONS は script.md と文字単位で一致**させる（コピーして改変しない）
5. 必須ビジュアル：S1またはS7に**サムネに使える絵**（大きな数字・対比・Before/After）／**エピソード固有の図解を1つ以上**（独立SVGは幅を`min(78cqw,800px)`のようにcqw基準で指定）
6. **STEPS密度検査**：`retention-packaging.md` §4 のスクリプトでPASSさせる（STEP数≥音声秒数÷7、無変化15秒以内）。STEPを増やす手段は既存アニメクラスでの順次出現のみ
7. **Playwright検証**：pageerrors 0件／`SLIDES_META`・`NARRATIONS`・`section.slide` すべて18で一致／全idがDOMに存在。主要スライドのスクリーンショットで実寸確認（図が縮んでいないか）

## 完了条件（全て）
- [ ] NARRATIONS一致（検証スクリプトの出力）
- [ ] §4 STEPS密度PASS（出力を報告）
- [ ] Playwright 0エラー・18整合（出力を報告）

## 引き継ぎ
→ **yt-qa**（最終検品）。動画化の指示があれば → **yt-video-editor**
