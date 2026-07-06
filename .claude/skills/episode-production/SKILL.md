---
name: episode-production
description: Create, upgrade, or renew an episode of the "AI時代のマーケティング・ラボ" YouTube course (script.md / description.md / slide.html / shorts.md) in the 18-slide "big style" format, following the retention/packaging spec v2 (docs/youtube-reform-plan.md). Use when writing a brand-new episode (EP17+), when renewing an existing episode to the v2 format (L1 packaging / L2 opening / L3 full rewrite), or when fixing narration/timestamp/pronunciation issues.
when_to_use: "Triggers: 新しいエピソードを作って, EPNNを作成, EPNNをL1/L2/L3で更新, リニューアル, 計画書に従って更新, タイトル・サムネ見直し, スライド化して, ナレーション直して, Shorts台本"
---

# エピソード制作スキル（18枚 big style）

このリポジトリの全エピソードは `script.md` + `description.md` + `slide.html` の3ファイル組で、
`slide.html` は **18枚・big style**（cqwベースの大きい文字、モバイル前提）で統一されている。
EP02〜EP08 はこの形式が完成済み。EP09〜EP12 はこの形式へアップグレード済み。
**EP13〜EP24 はまだ空テンプレート**（`script.md`/`description.md` は未執筆プレースホルダー、`slide.html` 自体が存在しない）。

最初にやること：対象エピソードの現状を `ls <episode_dir>/` で確認し、以下のどちらに該当するか判定する。

| 状態 | 該当エピソード | フロー |
|------|----------------|--------|
| `slide.html` が無い／`script.md`が空テンプレート | EP17〜24 | **A. 新規エピソード作成フロー**（v2仕様で作る） |
| `slide.html` はあるが 13〜15枚（旧フォーマット） | （現状は無し、将来の参考用） | **B. 既存スライド刷新フロー** |
| 18枚あるが**旧v1構成**（シラバス型タイトル・定型オープニング） | EP01〜EP16 | **C. リニューアルフロー（L1/L2/L3）** |

**フローC（リニューアル）**：`docs/youtube-reform-plan.md` のロードマップに従い、
[retention-packaging.md](retention-packaging.md) の作業レベル定義（L1=パッケージのみ／L2=冒頭改修／L3=全面リライト）で実施する。
「EP◯◯をL3で更新して」のような指示が来たら retention-packaging.md を開いて該当レベルの範囲だけ作業する。
L3はフローAと同じ工程＋パッケージング先行＋機械検査（ナレーション検査・STEPS密度検査）＋Shorts台本3本。

参照ファイル（必要な時だけ読む。常時読み込み不要）：
- [retention-packaging.md](retention-packaging.md) — **維持率・パッケージング仕様v2**（タイトル/サムネ/検索KW先行、コールドオープン、ナレーション機械検査、STEPS密度基準、Shorts）。根拠は `docs/youtube-reform-plan.md`
- [story-writing.md](story-writing.md) — **ストーリー設計ガイド**（事例リサーチ→ワークシート→文体ルール→10点ルーブリック採点。台本前の必須工程）
- [design-system.md](design-system.md) — CSS/HTML/JSの構造（big styleコンポーネント、ページ番号markup、SLIDES_META/NARRATIONS形状）
- [narration-rules.md](narration-rules.md) — VOICEVOX訓読み対策・ABBR_MAP・尺の計算式
- [templates.md](templates.md) — `script.md`/`description.md` の正確なテンプレートと記入例
- 完成済みの実例として **`02_intermediate/ep08_usp-differentiation/`** をHTML構造のお手本にする（※台本構成のお手本としては旧式。**台本の構成・ナレーションの書き方は retention-packaging.md の v2 仕様が最優先**）

---

## 全24回ロードマップ（前後回リンク用）

| 回 | タイトル | ディレクトリ |
|----|----------|------------|
| 1 | そもそもマーケティングとは？「売れる仕組み」の正体 | `01_beginner/ep01_what-is-marketing/` |
| 2 | 誰に何を売る？「3C分析」と「STP分析」の超基本 | `01_beginner/ep02_3c-stp-analysis/` |
| 3 | 顧客の悩みを見つける「ペルソナ設定」の落とし穴 | `01_beginner/ep03_persona-pitfalls/` |
| 4 | 商品の魅力を言語化する「ベネフィット」と「特徴」の違い | `01_beginner/ep04_benefit-vs-feature/` |
| 5 | 買いたくなる流れを作る「カスタマージャーニー」の描き方 | `02_intermediate/ep05_customer-journey/` |
| 6 | 価格設定の心理学。安売りせずに選ばれる「プライシング戦略」 | `02_intermediate/ep06_pricing-psychology/` |
| 7 | デジタル時代の「4P」と「4C」。現代版マーケティングミックス | `02_intermediate/ep07_4p-4c-mix/` |
| 8 | 競合と差別化する「USP（独自の強み）」の見つけ方 | `02_intermediate/ep08_usp-differentiation/` |
| 9 | 広告費を無駄にしない！「CPA」と「LTV」の考え方 | `03_practical/ep09_cpa-ltv/` |
| 10 | 反応率が激変する「コピーライティング」5つの法則 | `03_practical/ep10_copywriting-5laws/` |
| 11 | SNS運用の本質。フォロワー数より大切な「エンゲージメント」 | `03_practical/ep11_sns-engagement/` |
| 12 | データを改善に繋げる「ABテスト」の正しいやり方 | `03_practical/ep12_ab-testing/` |
| 13 | AIで市場調査を10倍速くする。プロンプトのコツ | `04_ai-usage/ep13_ai-market-research/` |
| 14 | AIによるコンテンツ制作。記事執筆から画像生成までのワークフロー | `04_ai-usage/ep14_ai-content-creation/` |
| 15 | データ分析はAIに任せる。顧客アンケートの自動集計と考察 | `04_ai-usage/ep15_ai-data-analysis/` |
| 16 | 24時間働く営業マン。AIチャットボットによる接客デザイン | `04_ai-usage/ep16_ai-chatbot/` |
| 17 | ブランド・エクイティの構築。「指名検索」される状態をどう作るか | `05_advanced/ep17_brand-equity/` |
| 18 | LTV（顧客生涯価値）最大化のCRM戦略 | `05_advanced/ep18_ltv-crm-strategy/` |
| 19 | マーケティング組織の構築とマネジメント | `05_advanced/ep19_marketing-org/` |
| 20 | グロースハックとスケールアップ | `05_advanced/ep20_growth-hack/` |
| 21 | なぜあのお店は行列ができるのか？身近なヒット商品の裏側 | `06_case-studies/ep21_hit-products/` |
| 22 | 大逆転のマーケティング。倒産寸前からV字回復した企業の共通点 | `06_case-studies/ep22_v-shaped-recovery/` |
| 23 | 失敗事例から学ぶ。「良い商品なのに売れない」3つの理由 | `06_case-studies/ep23_failure-cases/` |
| 24 | これからの時代に生き残るマーケターの条件 | `06_case-studies/ep24_future-marketer/` |

「関連動画」セクションの前回・次回はこの表から拾う。最終回（24）に次回は無いので「シリーズ最終回」と書く。

---

## A. 新規エピソード作成フロー（EP13〜24向け）

対象エピソードの `script.md`/`description.md` は空のプレースホルダー（`XX分`・`ポイント①`等）。
**実際のマーケティング知見を自分で執筆する**必要がある（既存ファイルからの転記ではない）。

1. **題材を理解する**：ディレクトリ名・README記載タイトルから扱うトピックを把握する（上表参照）。同シリーズの既存回のトーン・難易度感を踏襲する。
2. **パッケージングを先に決める**：[retention-packaging.md](retention-packaging.md) §1に従い、検索KW・タイトル3案・サムネ文字・「サムネの約束」を**台本より先に**決めて script.md に記録する。タイトル合格条件を全て満たすこと。
3. **ストーリーを設計する**：[story-writing.md](story-writing.md) の手順で、①事例リサーチ（WebSearch・出典必須）→②ストーリー設計ワークシート記入→③[retention-packaging.md](retention-packaging.md) §2の**動画構造v2**（S1コールドオープン → S2約束＋オープンループ → S3-6ケーススタディ → S7リフック① → S8-11原則 → S12リフック② → S13-15適用 → S16-17回収 → S18次への開ループ）への流し込みで18枚の見出しリストを作る。HTML構造の参考はEP08。
   - ナレーション執筆後は story-writing.md §5の**10点ルーブリックで自己採点し、8点未満なら書き直す**（採点表を制作メモに残す）。
4. **`script.md` を執筆する**：[templates.md](templates.md) の構成に従い、`## 動画基本情報` → `### パッケージング` → `### 主な引用・参考文献`（実在する理論・統計の出典を最低3〜5件入れる。架空の出典は禁止）→ `## 構成（全18スライド／約X分Y秒）` → 18×`### スライド N：タイトル（start〜end）`ブロック → `## 制作メモ`（主オープンループの張り・回収スライドを明記）。
   - 各ブロックの **`**ナレーション：**`** は完成原稿。後で `slide.html` の `NARRATIONS[N-1]` に **そのまま** コピーする（食い違いを作らない）。
   - 時間（start〜end）は [narration-rules.md](narration-rules.md) の文字数換算式で算出した暫定値でよい（動画ビルド後に実測値で再修正するため）。
5. **ナレーション機械検査を通す**：[retention-packaging.md](retention-packaging.md) §3のスクリプトを実行し、PASSになるまで書き直す（冒頭禁止句・接続詞監査・問いかけ密度・開ループ）。
6. **`description.md` を執筆する**：[templates.md](templates.md) のYouTube概要欄テンプレートに従い全セクションを埋める。冒頭2行に検索KWを含める（[retention-packaging.md](retention-packaging.md) §5）。
7. **`slide.html` を新規作成する**：EP08の `slide.html` を丸ごとコピーしてベースにし、[design-system.md](design-system.md) を見ながら以下を差し替える：
   - `<title>`、アクセントカラー（既存回と被らない色を選ぶ。ヘッダコメント `/* EPNN accent: ... */` に明記）
   - ステージ本体（`<section class="slide" id="s1">`〜`id="s18"`）の中身を18枚分書き換え
   - `SLIDES_META` / `NARRATIONS` / `TOTAL_SECS` を4.で書いた内容に合わせて差し替え
   - フラッグシップSVG（天秤・レーダー図など）やCSSの巨大ブロック・`@keyframes`は基本流用し、内容に応じて要素だけ調整する
8. **検証する**：[design-system.md](design-system.md) のPlaywright検証手順（JSエラー0件・18件一致）に加え、[retention-packaging.md](retention-packaging.md) §4の**STEPS密度検査**（5〜7秒毎の視覚変化・15秒超の静止禁止）をPASSさせる。
9. **略語の発音チェック**：NARRATIONSに新しい英字略語が出たら [narration-rules.md](narration-rules.md) のABBR_MAP/COMPOUND_DICTに追加する。
10. **Shorts台本を書く**（L3・新規作成時）：[retention-packaging.md](retention-packaging.md) §6に従い `shorts.md` に3本。
11. **動画ビルドはユーザーから明確に指示された時だけ実行する**（「スライド・ナレーションの更新」だけを頼まれた場合はビルドしない）。ビルドする場合は動画生成フローを使う。

---

## B. 既存スライド刷新フロー（旧フォーマット→18枚）

EP02〜EP08で実施済みのフロー。`script.md`に実内容が既にある回を対象に、内容を保持したまま18枚へ再構成する。

1. 旧 `slide.html` を `slide_reference.html` として退避（バックアップ。以後このファイルは編集しない）
2. 既存 `script.md` のナレーション内容を読み、**新規執筆を最小化**して18枚に再分割（1スライド1コンセプトの原則。濃いスライドを2〜3枚に割る）
3. [design-system.md](design-system.md) の「大原則」に従い、CSS・base64フォント・JSエンジン・`@keyframes`・フラッグシップSVGは一切触らず、ステージ本体とJSデータ配列の2か所だけ置換する
4. `script.md`／`description.md` を新18枚構成に合わせて全面リライト（[templates.md](templates.md)のテンプレートに従う）
5. A.の6〜7と同じ検証・略語チェックを行う

---

## 動画ビルド後のタイムスタンプ修正（重要・全エピソード共通）

`slide.html` 内の `SLIDES_META`/`TOTAL_SECS` は**ビルド前の文字数推定値であり、ビルド後も自動更新されない**
（`_tools/video/make_video.py` はこれらを読むだけで書き戻さない）。実際の音声合成後の尺は推定と数%〜十数%ずれることがある。

**動画を実際にビルドした場合は、必ず実測値で `script.md`/`description.md` のタイムスタンプを修正すること**：

```bash
cd <episode_dir>/video_build/out/.work/slides
python3 -c "
import subprocess
durs = []
n = 18  # スライド枚数
for i in range(n):
    out = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
        '-of','default=noprint_wrappers=1:nokey=1', f'slide_{i:02d}.mp4'],
        capture_output=True, text=True).stdout.strip()
    durs.append(float(out))
cum = 0.0
for i, d in enumerate(durs):
    start, cum = cum, cum + d
    m, s = int(start // 60), start % 60
    print(i + 1, f'{m}:{s:05.2f}')
"
```

この実測値（秒の小数部分は切り捨てでよい）を `script.md` の全`### スライド N：...（start〜end）`見出しと、
`description.md` の `## タイムスタンプ`／`## チャプター生成用` セクションに反映する。`slide.html` 自体の
`SLIDES_META`/`TOTAL_SECS` は触らなくてよい（ビルド用の推定値として残す）。

---

## 動画生成コマンド（ビルドを明示的に頼まれた時のみ）

```bash
python3 _tools/video/make_video.py \
  <episode_dir>/slide.html \
  --out <episode_dir>/video_build/out \
  --speaker 11 --speed 1.1 --final-outro 3.0
```

実行環境のセットアップ・トラブルシュートは [narration-rules.md](narration-rules.md) の末尾を参照。
