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
| 表示テキスト（t-md／hl-banner）の行長 | 1行24字以内。超える文は**必ず明示的`<br>`**で割る（自動折返しに任せない） |
| **ぶら下がり禁止** | 折返し・`<br>`の結果、**1〜3字だけの行**（例：「…分か／る」）を作らない。各行4字以上になる位置で切る |
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

**STEPSの順序＝ナレーションの話順にする（重要）。** ビルド時、make_video.py は各STEPの
**画面上テキストとナレーション文を照合**し、そのSTEPの内容を話し始める文の頭（`lead`秒前）に
発火させる（content-matched sync。照合できないSTEPは前後アンカー間で補間）。
つまり「要素の見出し語・数字がナレーションの対応文と同じ語を含む」ように書けば自動で完全同期する。
STEPの並び順は話順にすること（照合は前方一方向に探索する）。
slide.html内の`t:`値はブラウザプレビュー用の概算にすぎない（ビルドはsi/ids/animだけを使う）。
ビルドログの `narration sync: N/M steps text-anchored` で照合率を確認できる（7割以上が目安）。

### カラー＆タイポグラフィ v2.1（人気動画リサーチ反映・全話共通の文法）

根拠：国内人気チャンネル（リベ大=暗背景×高コントラスト白、中田式=太/細マーカー2段階、
ずんだもん系=黄色強調）＋Kurzgesagt（暗ベース+高彩度アクセント少数）＋WCAG/BBC/CUDの数値基準。

**配色（70:25:5）**
| トークン | 値 | 役割 |
|---------|-----|------|
| ベース | `#0B1220`系の暗紺（既存） | 背景70% |
| テキスト | `#EEEEF8`（既存） | 本文25% |
| **キーイエロー** | `--key:#FFD54F`（**全話共通・固定**） | **結論キーワード・重要バナー**のみ（5%）。CUDの「黒背景では黄/白」原則。「黄色=覚える所」を視聴者に学習させる |
| 話数アクセント | `--accent`（話数ごと） | 見出し帯・図形・チップ枠・**数字/固有名詞**用。結論の文字色には使わない（役割分離） |

**話数アクセントの選定制約**：暗紺上でWCAG 3:1以上（暗い紫・純青・暗赤・グレーはNG。
indigo #6366F1 / slate #64748B は基準未満なので今後の新規回では選ばない）。
候補例：teal #14B8A6 / fuchsia #D946EF / amber #F59E0B / cyan #06B6D4 / lime #84CC16 /
orange #F97316 / pink #F472B6。**赤と緑を同一画面で対比させない**。

**タイポグラフィ**
- フォントはNoto Sans CJK JP継続。**見出し・キーワード＝Black(900)／本文＝Medium(500)** の2段階
  （中田式の太/細マーカー構造。※900の実レンダリングには `fonts-noto-cjk-extra` が必要——setup_env.shが自動導入）
- サイズ下限（720p実寸）：本文26px／キーワード44px以上／注釈22px未満禁止（BBC 8%則＋国内実務値。
  既存のcqwクランプは1280px幅でこれを満たす＝最小値を下げない）
- 行間1.4前後、1スライドの箇条書きは3〜4行まで

**強調は2種類に限定**（混在禁止）
1. **結論＝キーイエロー太字**（`.c-accent`スパン＝v2.1からイエロー）
2. **数字・固有名詞＝話数アクセント**（`.bignum`等）
下線・枠・その他の色替えは使わない。色だけに頼らず必ず太字/サイズを併用。

各エピソードの `:root { --accent: ...; --glow-acc: ...; }` オーバーライドと
`/* EPNN accent: 色名 */` コメント、既存回とのgrep重複確認は従来どおり。

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
