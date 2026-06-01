# スライドコンポーネントガイド v2

## パイプライン（必読）

```bash
# 組み立て
python3 /tmp/verify-slides/assemble.py /tmp/verify-slides/content_epNN.py <出力先>
# 検証
node /tmp/verify-slides/verify-one.js <出力先>
```

テンプレート: `/home/user/Marketing-learn-contents/02_intermediate/ep05_customer-journey/slide.html`

---

## コンテンツモジュール構造

```python
TITLE        = "第N回 タイトル | AI時代のマーケティング・ラボ"
EP_CSS       = r"""..."""   # <style id="ep-css"> 内に入るCSS
SLIDES_HTML  = r"""..."""   # 13個の <section class="slide"> ブロック
STEPS        = """..."""    # const STEPS = [...] の中身
META         = """..."""    # const SLIDES_META = [...] の中身 (13エントリ必須)
NARR         = """..."""    # const NARRATIONS = [...] の中身 (13個のバッククォート文字列)
```

## EP_CSS の書き方

```css
/* ── vertical centering（必ず先頭に含める） ── */
.pad   { justify-content: center; }
.pad-t { justify-content: center; }

/* ── このエピソードのアクセント色上書き ── */
:root { --accent: #14B8A6; --glow-acc: rgba(20,184,166,.25); }

/* ── エピソード固有CSS ── */
.my-class { ... }
```

## SLIDES_HTML の基本構造

```html
  <!-- S1: Title 0-30s -->
  <section class="slide active" id="s1" style="background:radial-gradient(ellipse 90% 75% at 62% 45%,#1a1260 0%,var(--slide-bg) 68%);align-items:center;justify-content:center;text-align:center;">
    <div class="s1-ring s1-ring1" aria-hidden="true"></div>
    <div class="s1-ring s1-ring2" aria-hidden="true"></div>
    <div class="s1-ring s1-ring3" aria-hidden="true"></div>
    <div class="s1-dot s1-dot1" aria-hidden="true"></div>
    <div class="s1-dot s1-dot2" aria-hidden="true"></div>
    <div class="s1-dot s1-dot3" aria-hidden="true"></div>
    <div class="slide-num">01 / 13</div><div class="step-dots" id="sd1"></div>
    <div class="s1-content">
      <div id="s1-badge" class="se" style="display:inline-flex;align-items:center;gap:.5em;background:var(--surf2);border:1px solid rgba(124,111,255,0.4);color:var(--muted2);border-radius:20px;padding:.3em 1.2em;margin-bottom:.75em;font-size:clamp(9px,1.2vw,14px);"><i class="fa-solid fa-circle-play" style="color:var(--accent);"></i>&ensp;AI時代のマーケティング・ラボ</div>
      <div id="s1-ep" class="se" style="font-size:clamp(11px,1.5vw,18px);color:var(--muted2);font-weight:700;margin-bottom:.3em;letter-spacing:.05em;">第N回</div>
      <div id="s1-title" class="se t-xl" style="color:#fff;letter-spacing:-.02em;">メインタイトル</div>
      <div id="s1-sub" class="se" style="color:var(--accent);font-size:clamp(15px,2.5vw,32px);font-weight:700;margin-top:.4em;">「サブタイトル」</div>
      <div id="s1-catch" class="se" style="color:var(--muted2);font-size:clamp(11px,1.6vw,20px);margin-top:.6em;">キャッチコピー</div>
    </div>
  </section>

  <!-- S2〜S12: コンテンツスライド -->
  <section class="slide" id="s2">
    <div class="slide-num">02 / 13</div><div class="step-dots" id="sd2"></div>
    <div class="pad">
      <div class="sh se" id="s2-hd">見出し</div>
      <!-- コンテンツ -->
    </div>
  </section>

  <!-- S13: 次回予告 -->
  <section class="slide" id="s13">
    <div class="slide-num">13 / 13</div><div class="step-dots" id="sd13"></div>
    <div class="pad" style="align-items:center;justify-content:center;text-align:center;">
      <div id="s13-card" class="se card" style="...">
        <div class="next-lbl"><i class="fa-solid fa-forward"></i> 次回</div>
        <div class="next-title">次回タイトル</div>
        <!-- 内容 -->
      </div>
      <div id="s13-cta" class="se"><i class="fa-solid fa-heart"></i> チャンネル登録 &amp; 高評価をお願いします！ <i class="fa-solid fa-thumbs-up"></i></div>
    </div>
  </section>
```

**必須ルール:**
- S1のみ `class="slide active"` — S2〜S13 は `class="slide"`
- 各スライドに `<div class="slide-num">NN / 13</div><div class="step-dots" id="sdN"></div>`
- STEPSの `ids` に書くIDは必ず `.se` 付き要素に存在させる
- 全体を `<div class="pad">` または `<div class="pad-t">` で囲む

---

## 利用可能なコンポーネント

### GAUGE BAR（ゲージバー）
数値の割合・比率表示。入場時にアニメーション充填。

```html
<div class="gauge-wrap se" id="...">
  <div class="gauge-hd">LTV ÷ CPA 比率</div>
  <div class="gauge-track">
    <div class="gauge-fill" style="--v:.75;--c:var(--green)"></div>
    <span class="gauge-marker" style="left:33%">3× 目安</span>
  </div>
  <div class="gauge-legs"><span>0</span><span>3×</span><span>10+</span></div>
</div>
```
`--v`: 0〜1の割合　`--c`: 色（CSS変数OK）

---

### KPI BIG（大きな数値表示）

```html
<div class="kpi-wrap se" id="...">
  <div class="kpi-big" style="--c:var(--green)">
    <div class="kpi-num">9.9×</div>
    <div class="kpi-sub">LTV / CPA 比率</div>
  </div>
  <div class="kpi-ctx">
    <strong>目安は3×以上</strong><br>A社は黄金比率を<br>大幅に超えた
  </div>
</div>
```

---

### HORIZONTAL BAR CHART（横棒グラフ）

```html
<div class="bar-chart-h se" id="...">
  <div class="bh-row">
    <span class="bh-lbl">CTR 1%</span>
    <div class="bh-track"><div class="bh-fill" style="--v:50;--c:var(--muted)"></div></div>
    <span class="bh-val" style="color:var(--muted)">CPA 20,000円</span>
  </div>
  <div class="bh-row">
    <span class="bh-lbl">CTR 2%</span>
    <div class="bh-track"><div class="bh-fill" style="--v:100;--c:var(--green)"></div></div>
    <span class="bh-val" style="color:var(--green)">CPA 10,000円</span>
  </div>
</div>
```
`--v`: 0〜100のパーセント値

---

### 2×2 MATRIX（4象限マトリクス）

```html
<div class="matrix-2x2 se" id="...">
  <div class="mx-cell mx-tl hi">
    <div class="mx-hd"><i class="fa-solid fa-star"></i> 最優先</div>
    <div class="mx-body">ヘッドライン変更<br>CTAボタン色</div>
  </div>
  <div class="mx-cell mx-tr">
    <div class="mx-hd">次点</div>
    <div class="mx-body">画像差し替え</div>
  </div>
  <div class="mx-cell mx-bl">
    <div class="mx-hd">低優先</div>
    <div class="mx-body">フォント変更</div>
  </div>
  <div class="mx-cell mx-br hi-g">
    <div class="mx-hd">長期施策</div>
    <div class="mx-body">動画制作</div>
  </div>
</div>
<div class="mx-labels">
  <span class="mx-lbl-x">← 変更しやすい ── 変更しにくい →</span>
  <span class="mx-lbl-x" style="text-align:right">↑ 高インパクト</span>
</div>
```
ハイライト: `.hi`（アクセント）`.hi-g`（グリーン）`.hi-r`（レッド）`.hi-y`（イエロー）

---

### STAT RING（SVGドーナツ）
circumference of r=38 ≈ 239

```html
<div class="stat-rings se" id="...">
  <div class="stat-ring-wrap">
    <div class="stat-ring" style="--v:80;--c:#4ade80">
      <svg viewBox="0 0 100 100">
        <circle class="sr-track" cx="50" cy="50" r="38"/>
        <circle class="sr-fill"  cx="50" cy="50" r="38"/>
      </svg>
      <div class="sr-inner"><div class="sr-val">80%</div><div class="sr-lbl">継続率</div></div>
    </div>
    <div class="stat-ring-ttl">定期購入顧客</div>
  </div>
</div>
```
`--v`: 0〜100　`--c`: 色

---

### NUMBER STEPS（番号付きステップ）

```html
<div class="n-steps">
  <div class="n-step se" id="s3-s1">
    <div class="n-num">1</div>
    <div class="n-body"><strong>ペルソナを定める</strong><div class="t-sm">「誰の、何の問題を解決するか」を一行で書く</div></div>
  </div>
  <div class="n-step se" id="s3-s2">
    <div class="n-num g">2</div>
    <div class="n-body"><strong>競合USPを調べる</strong><div class="t-sm">Amazonレビュー・Twitter・顧客インタビューで収集</div></div>
  </div>
</div>
```
番号色: デフォルト=アクセント、`.g`=グリーン、`.r`=レッド、`.b`=ブルー

---

### HORIZONTAL FLOW（水平フロー図）

```html
<div class="h-flow se" id="...">
  <div class="h-flow-node accent">Aware<span class="fn-sub">認知</span></div>
  <svg class="h-arrow" viewBox="0 0 24 24" fill="none"><path d="M5 12h14M14 7l5 5-5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
  <div class="h-flow-node blu">Appeal<span class="fn-sub">訴求</span></div>
  <svg class="h-arrow" viewBox="0 0 24 24" fill="none"><path d="M5 12h14M14 7l5 5-5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
  <div class="h-flow-node ylw">Ask<span class="fn-sub">調査</span></div>
  <svg class="h-arrow" viewBox="0 0 24 24" fill="none"><path d="M5 12h14M14 7l5 5-5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
  <div class="h-flow-node acc2">Act<span class="fn-sub">行動</span></div>
  <svg class="h-arrow" viewBox="0 0 24 24" fill="none"><path d="M5 12h14M14 7l5 5-5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
  <div class="h-flow-node grn">Advocate<span class="fn-sub">推薦</span></div>
</div>
```
ノード色: `accent` `acc2` `grn` `blu` `ylw`（デフォルトは無色）

---

### QUOTE BLOCK（引用ブロック）

```html
<blockquote class="quote-blk se" id="...">
  <p class="qb-text">「コピーライティングとは、<em>紙の上のセールスマン</em>である」——24時間働き、何千人もの顧客に同時に語りかける</p>
  <cite class="qb-cite">David Ogilvy 『Ogilvy on Advertising』 1983</cite>
</blockquote>
```

---

### COMPARISON TABLE（比較表）

```html
<div class="comp-tbl se" id="...">
  <div class="comp-row comp-head">
    <span class="comp-label"></span>
    <span class="comp-a">施策前</span>
    <span class="comp-b">施策後</span>
  </div>
  <div class="comp-row">
    <span class="comp-label">プラン数</span>
    <span class="comp-a">1プラン</span>
    <span class="comp-b">3プラン</span>
  </div>
  <div class="comp-row hi">
    <span class="comp-label">CVR</span>
    <span class="comp-a c-red">0.8%</span>
    <span class="comp-b c-green">2.3%</span>
  </div>
</div>
```

---

### FORMULA（数式表示）

```html
<div class="formula se" id="...">
  <span class="fm-var" style="--c:var(--accent)">LTV</span>
  <span class="fm-op">÷</span>
  <span class="fm-var" style="--c:var(--acc2)">CPA</span>
  <span class="fm-op">&gt;</span>
  <span class="fm-val" style="--c:var(--green)">3</span>
</div>
<div class="formula-sub se" id="...">これが「健全な投資」の目安</div>
```

---

### INLINE SVG（ベルカーブ・ファネル・カスタム図解）

```html
<svg class="svg-il se" id="..." viewBox="0 0 400 160" aria-hidden="true">
  <!-- グリッドライン -->
  <line class="svg-grid" x1="0" y1="120" x2="400" y2="120"/>
  <line class="svg-grid" x1="200" y1="0" x2="200" y2="140"/>
  <!-- ベルカーブA -->
  <path class="svg-area" d="M40,120 C80,120 100,10 200,10 C300,10 320,120 360,120 Z"/>
  <path class="svg-curve" d="M40,120 C80,120 100,10 200,10 C300,10 320,120 360,120"/>
  <!-- 有意差マーカー -->
  <line class="svg-marker" x1="240" y1="10" x2="240" y2="120"/>
  <!-- ラベル -->
  <text class="svg-lbl-a" x="195" y="145" text-anchor="middle">A案 (対照)</text>
</svg>
```

---

### HIGHLIGHT BANNER（強調バナー）

```html
<div class="hl-banner se" id="..." style="--c:var(--green)">
  <i class="fa-solid fa-circle-check hb-icon"></i>
  <div class="hb-text"><strong>顧客維持率5%改善→利益25〜95%増加</strong><br>Bain &amp; Company / Reichheld 研究</div>
</div>
```

---

### VERDICT ROWS（OK/NG リスト）

```html
<div class="verdict-rows se" id="...">
  <div class="verdict-row ng">
    <i class="fa-solid fa-xmark v-icon"></i>
    <div class="v-body"><strong>CPAだけ見る</strong>：獲得コスト安くても赤字になる</div>
  </div>
  <div class="verdict-row ok">
    <i class="fa-solid fa-check v-icon"></i>
    <div class="v-body"><strong>LTV÷CPAで見る</strong>：投資対効果を正確に判断できる</div>
  </div>
</div>
```

---

### STEP-FLOW（縦フロー）

```html
<div class="step-flow">
  <div class="sf-item se" id="s3-step1">
    <div class="sf-dot"></div>
    <div class="sf-body"><strong>顧客セグメントを決める</strong><div class="t-sm">who / pain / gain を一行で</div></div>
  </div>
  <div class="sf-item se" id="s3-step2">
    <div class="sf-dot"></div>
    <div class="sf-body"><strong>競合USPを収集する</strong></div>
  </div>
</div>
```

---

### TAGS / PILLS（タグ・バッジ）

```html
<span class="tag tag-a">インパクト高</span>
<span class="tag tag-g">変更容易</span>
<span class="tag tag-r">注意</span>
<span class="pill acc">実践編</span>
```

---

## STEPS・META・NARR の規約

```python
STEPS = """  {si:0,  t:0,    ids:['s1-badge'],          anim:'rv-fade'},
  {si:0,  t:0.8,  ids:['s1-ep'],             anim:'rv-fade'},
  {si:0,  t:1.5,  ids:['s1-title'],          anim:'rv-up'},
  {si:0,  t:2.5,  ids:['s1-sub'],            anim:'rv-up'},
  {si:0,  t:3.5,  ids:['s1-catch'],          anim:'rv-fade'},
  {si:1,  t:30,   ids:['s2-hd'],             anim:'rv-fade'},
  {si:1,  t:33,   ids:['s2-hook'],           anim:'rv-up'},
  ...
  {si:12, t:585,  ids:['s13-card'],          anim:'rv-scale'},
  {si:12, t:590,  ids:['s13-cta'],           anim:'rv-up'},"""

META = """  {id:'s1',  start:0,   end:30,  dotContainerId:'sd1'},
  {id:'s2',  start:30,  end:80,  dotContainerId:'sd2'},
  ...
  {id:'s13', start:585, end:600, dotContainerId:'sd13'},"""

NARR = """  `スライド1のナレーション（改行は\\nで）`,
  `スライド2のナレーション`,
  ...
  `スライド13のナレーション`,"""
```

**必須チェック：**
- `META`: 13エントリ、`s1.start=0`、`s13.end=600`、各エントリ連続
- `STEPS`: `ids` の各IDは SLIDES_HTML 内に `class="se"` 付きで存在すること
- `si` はスライド番号-1（s1→0、s13→12）
- `NARR`: 13個のバッククォート文字列

---

## アニメーション種類

| クラス | 効果 | 用途 |
|--------|------|------|
| `rv-fade`  | フェードイン | テキスト・ラベル全般 |
| `rv-up`    | 下から上にスライド | リスト・説明文 |
| `rv-left`  | 右から左 | カード・補足 |
| `rv-right` | 左から右 | 対比・反論 |
| `rv-scale` | 拡大フェード | 数字・KPI・重要ポイント |
| `rv-pop`   | バウンス拡大 | バッジ・アイコン・強調 |

ゲージ・バーチャート・リングは `rv-fade`/`rv-up`/`rv-scale` で自動的に充填アニメーションも起動。

---

## 完了条件

```
node /tmp/verify-slides/verify-one.js <出力先>
```

- `uniqueErrors`: `[]`
- `slideCount`: `13`
- `activeStart`: `"s1"`
- `finalSlide`: `"s13"`
- `visibleOnFinal`: `≥1`

これを満たすまで修正・再組み立てを繰り返す。完了後はコミット・プッシュしない（親が行う）。
