# big style デザインシステム / slide.html 構造リファレンス

## 大原則（既存スライドを刷新するとき）

- **CSS・base64フォント・JSエンジン・`@keyframes` は一切触らない**（巨大で壊すと復旧が大変）
- 置き換えるのは2か所だけ：
  1. ステージ本体（`<section class="slide" id="s1">` 〜 最後の `</section>` までの18枚分）
  2. JSデータ配列（`const SLIDES_META = [...]` 〜 `const NARRATIONS = [...]` 〜 `const TOTAL_SECS = N;`）
- フラッグシップ SVG 図（天秤・レーダー・ベン図など）とそのアニメーションは元のまま流用する
- ファイルは1MB超（base64フォント埋め込みのため）。`Read`で全部読まず、`grep -n`で行番号を特定して`sed -n 'A,Bp'`で部分読みする

## ページ番号・ドットmarkup（実例：EP08より）

```html
<section class="slide active" id="s1">
  <div class="slide-num">01 / 18</div><div class="step-dots" id="sd1"></div>
  <!-- スライド本体 -->
</section>
<section class="slide" id="s2">
  <div class="slide-num">02 / 18</div><div class="step-dots" id="sd2"></div>
  ...
</section>
```

- 最初のスライドだけ `class="slide active"`、以降は `class="slide"`
- `slide-num` は2桁ゼロ埋め＋` / 18`
- `step-dots` の `id` は `sd` + スライド番号（1始まり）

## JSデータ配列の形（実例：EP08より）

```js
const SLIDES_META = [
  {id:'s1', start:0.0, end:12.0, dotContainerId:'sd1'},
  {id:'s2', start:12.0, end:57.2, dotContainerId:'sd2'},
  // ... s18まで。start/endは秒。endが次のstartと連続する
];
const NARRATIONS = [
  `1段落目のテキスト。文末は必ず句読点。
2段落目のテキスト。`,
  `s2のナレーション...`,
  // ... 18件。NARRATIONS[i] は SLIDES_META[i]（= id:'s'+(i+1)）に対応
];
const TOTAL_SECS = 553; // SLIDES_META最後のend
```

- `SLIDES_META`/`NARRATIONS` は必ず同数（18）。`id="sN"` のDOM要素数とも一致させる
- start/endはビルド前の**推定値**。文字数換算式は [narration-rules.md](narration-rules.md) 参照
- タイミングの目安：見出し要素は `start`、続く要素は `start+0.5, +1.0, ...` と詰め、最後のnote（補足）だけ `start + dur*0.35` あたりに遅らせる（ブラウザプレビュー用の概算でよく、実際のタイミングは音声合成後にmake_video.pyが再計算する）

## コンポーネント早見表（big style）

```css
.t-xl { font-size: clamp(22px, 5.5cqw, 42px); } /* メインタイトル */
.t-lg { font-size: clamp(18px, 4.2cqw, 34px); } /* サブタイトル */
.t-md { font-size: clamp(15px, 3.5cqw, 28px); } /* 本文 */
.t-sm { font-size: clamp(12px, 2.8cqw, 22px); } /* 補足 */
```

`cqw`ベース（コンテナクエリ単位）で最小値を大きく設定する。`vw`ベースの小さい値（Referenceスタイル＝旧13/15枚フォーマット）は使わない。

| 用途 | コンポーネント | 備考 |
|------|--------------|------|
| メインタイトル | `.sh` + `.t-xl` | スライドの見出し |
| 本文テキスト | `.se` + `.t-md` | 説明文 |
| 2列比較 | `.duo` + `.pcard` | 左右に並べる |
| タグ列挙 | `.taglist` > `.tag` | キーワード強調 |
| フロー/矢印 | `.aflow` + `.achip` + `.aarrow` | ステップ説明 |
| バナー強調 | `.hl-banner` | 重要メッセージ |
| ボーダー行 | `border-left:6px solid` + padding | 事例などの行リスト |

### 1スライド1コンセプトの原則

- 1枚のスライドで伝えることは1つ
- ナレーション1〜2段落に対応
- 視覚要素（テキスト・図）だけでも概要が伝わる構成にする
- ナレーションだけ聞いても理解できる構成にする

### タイポグラフィ（改行・空白）基準 — 必須検査

**検査コマンド（統合検証に含まれる）**：`python3 _tools/checks/verify_episode.py <episode_dir>`

| ルール | 基準 |
|--------|------|
| 見出し（t-xl）の行長 | **1行14字以内・最大2行**。折り返しは自動に任せず、意味の切れ目（助詞・句点の後）に**明示的な`<br>`** |
| サブ見出し（t-lg）の行長 | 1行20字以内。超えるなら`<br>`か文言短縮 |
| 行頭禁則 | `<br>`直後に 。、！？」』）・小書き仮名・ー を置かない（切る位置を前後にずらす） |
| 空白での位置調整禁止 | 全角スペース連続で位置を作らない。位置はflex/grid/gap/marginで組む |
| 余白の段階 | `margin-top`は 0.15〜1.2em の範囲（それ以上はレイアウト構造で解決）。要素間gapは `.4〜.7em` または `2〜4cqw` |
| 改行位置の意味 | 「変えたのは仕組み。ただし〜」→ 句点後で改行（`。<br>`）。名詞の途中・助詞の直前で切らない |
| 文字揃え | 同一スライド内の並列要素（タグ・カード）は文字数をなるべく揃える（±3字） |

### STEPS密度（テンポ）基準 — 必須検査

**各スライドのSTEP数 ≥ 音声秒数÷7（切り上げ）、15秒超の無変化区間禁止。**
検証スクリプトと増やし方は [retention-packaging.md](retention-packaging.md) §4。
STEPを増やすときは既存アニメクラス（rv-fade/rv-up/rv-scale/rv-pop）で要素を順次出現させる。
新しいCSS/JSエンジンは作らない。

### アクセントカラー

各エピソードごとに `:root { --accent: ...; --glow-acc: ...; }` をCSS内でオーバーライドしている
（コメント `/* EPNN accent: 色名 */` を付ける）。既存回と被らない色を選ぶこと
（EP05=purple #7c6fff、EP09=teal #14B8A6 など。新規エピソードは既存ファイルをgrepして使用済みの色を確認する）。

## 新規 slide.html を作る場合（EP13以降）

ゼロから組むのではなく、**直近の完成回（`02_intermediate/ep08_usp-differentiation/slide.html`）を丸ごとコピー**して
ベースにする。差し替えるのは「ページ番号・ドットmarkup」「JSデータ配列」「ステージ本体（テキスト・図解）」と
アクセントカラーのCSS変数のみ。CSSの骨格・フォント・アニメーションエンジン部分は触らない。

## 検証（Playwright・必須）

スライド本体・JSデータを書き換えたら、ブラウザで実際にレンダリングしてエラーが無いことを確認する：

```python
# JSエラー0件 + 全 SLIDES_META.id が DOM に存在することを確認
missing = pg.evaluate("""()=>{
  const m=[];
  SLIDES_META.forEach(s=>{ if(!document.getElementById(s.id)) m.push(s.id); });
  return m;
}""")
# missing == [] かつ
# section数(id="sN") == SLIDES_META.length == NARRATIONS.length == 18
# であることを確認する
```

## よくある問題と対処

| 問題 | 原因 | 対処 |
|------|------|------|
| スマホで文字が小さい | Referenceスタイル（vwベース）を使用 | Big style（cqwベース）に差し替え |
| 独立SVG図が小さく表示される | `.se`コンテナがshrink-wrapし`%`幅が潰れる（EP07 S12で実例） | SVGの`style`を`width:min(78cqw,800px)`のように**cqw基準**で指定し、親divに`width:100%`。描画後にPlaywrightで`getBoundingClientRect()`の実寸を確認 |
| アニメーション（`epN-pulse`等）が消える | slide.html再構築時にCSSを削除 | 元ファイルから`@keyframes`ブロックをコピー（ステージとJSのみ置換すれば起きない） |
| `Read`でファイルを開けない（1MB超） | base64フォントで巨大 | `sed`/`grep`で必要箇所だけ部分読み |
