---
name: episode-production
description: Create or upgrade an episode of the "AI時代のマーケティング・ラボ" YouTube course (script.md / description.md / slide.html) to the 18-slide "big style" format. Use when writing a brand-new episode from its blank template (EP13+), when upgrading an old 13/15-slide episode to 18 slides, or when fixing narration/timestamp/pronunciation issues in an existing episode.
when_to_use: "Triggers: 新しいエピソードを作って, EP13/14/.../24を作成, スライド化して, 18枚構成にアップデート, ナレーション直して, big styleにして"
---

# エピソード制作スキル（18枚 big style）

このリポジトリの全エピソードは `script.md` + `description.md` + `slide.html` の3ファイル組で、
`slide.html` は **18枚・big style**（cqwベースの大きい文字、モバイル前提）で統一されている。
EP02〜EP08 はこの形式が完成済み。EP09〜EP12 はこの形式へアップグレード済み。
**EP13〜EP24 はまだ空テンプレート**（`script.md`/`description.md` は未執筆プレースホルダー、`slide.html` 自体が存在しない）。

最初にやること：対象エピソードの現状を `ls <episode_dir>/` で確認し、以下のどちらに該当するか判定する。

| 状態 | 該当エピソード | フロー |
|------|----------------|--------|
| `slide.html` が無い／`script.md`が空テンプレート | EP13〜24 | **A. 新規エピソード作成フロー** |
| `slide.html` はあるが 13〜15枚（旧フォーマット） | （現状は無し、将来の参考用） | **B. 既存スライド刷新フロー** |
| 全部すでに18枚 | EP02〜EP12 | 触らない。タイムスタンプ修正だけなら 4.の手順を使う |

参照ファイル（必要な時だけ読む。常時読み込み不要）：
- [design-system.md](design-system.md) — CSS/HTML/JSの構造（big styleコンポーネント、ページ番号markup、SLIDES_META/NARRATIONS形状）
- [narration-rules.md](narration-rules.md) — VOICEVOX訓読み対策・ABBR_MAP・尺の計算式
- [templates.md](templates.md) — `script.md`/`description.md` の正確なテンプレートと記入例
- 完成済みの実例として **`02_intermediate/ep08_usp-differentiation/`** を常にお手本にする（最新で一番整理されている）

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

1. **題材を理解する**：ディレクトリ名・README記載タイトルから扱うトピックを把握する（上表参照）。同シリーズの既存回（特にEP08）のトーン・難易度感を踏襲する。
2. **18スライド構成を設計する**：EP08を開いて「フック → 定義 → 核心理論1〜3 → 実例 → まとめ → 次回予告」のような18枚の流れを参考にし、対象トピックに合わせた18枚の見出しリストを作る（オープニング1枚＋次回予告1枚を含む18枚が基本形）。
3. **`script.md` を執筆する**：[templates.md](templates.md) の構成に従い、`## 動画基本情報` → `### 主な引用・参考文献`（実在する理論・統計の出典を最低3〜5件入れる。架空の出典は禁止）→ `## 構成（全18スライド／約X分Y秒）` → 18×`### スライド N：タイトル（start〜end）`ブロック → `## 制作メモ`。
   - 各ブロックの **`**ナレーション：**`** は完成原稿。後で `slide.html` の `NARRATIONS[N-1]` に **そのまま** コピーする（食い違いを作らない）。
   - 時間（start〜end）は [narration-rules.md](narration-rules.md) の文字数換算式で算出した暫定値でよい（動画ビルド後に実測値で再修正するため）。
4. **`description.md` を執筆する**：[templates.md](templates.md) のYouTube概要欄テンプレートに従い、メイン説明文・タイムスタンプ・シリーズ再生リスト・関連動画（上のロードマップ表から前後回を引用）・参考資料・ハッシュタグ・チャプター生成用を全て埋める。
5. **`slide.html` を新規作成する**：EP08の `slide.html` を丸ごとコピーしてベースにし、[design-system.md](design-system.md) を見ながら以下を差し替える：
   - `<title>`、アクセントカラー（既存回と被らない色を選ぶ。ヘッダコメント `/* EPNN accent: ... */` に明記）
   - ステージ本体（`<section class="slide" id="s1">`〜`id="s18"`）の中身を18枚分書き換え
   - `SLIDES_META` / `NARRATIONS` / `TOTAL_SECS` を3.で書いた内容に合わせて差し替え
   - フラッグシップSVG（天秤・レーダー図など）やCSSの巨大ブロック・`@keyframes`は基本流用し、内容に応じて要素だけ調整する
6. **検証する**：[design-system.md](design-system.md) のPlaywright検証手順で、JSエラー0件・`SLIDES_META`/`NARRATIONS`/`id="sN"`の数が18件で一致することを確認する。
7. **略語の発音チェック**：NARRATIONSに新しい英字略語（例：新トピック特有の専門語）が出たら [narration-rules.md](narration-rules.md) のABBR_MAP/COMPOUND_DICTに追加する。
8. **動画ビルドはユーザーから明確に指示された時だけ実行する**（「スライド・ナレーションの更新」だけを頼まれた場合はビルドしない）。ビルドする場合は4.の動画生成フローを使う。

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
