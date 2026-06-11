# ナレーション作成スキル

このコースのスライド用ナレーション（`const NARRATIONS`）を作成・修正するときのガイドライン。

## プロジェクト概要

- コース名：AI時代のマーケティング・ラボ
- TTS エンジン：VOICEVOX（http://127.0.0.1:50021）
- 話者：11 = 玄野武宏 ノーマル
- 再生速度：1.1x
- 動画生成：`python3 _tools/video/make_video.py <slide.html> --out <outdir> --speaker 11 --speed 1.1`

---

## ナレーション構造

```js
const NARRATIONS = [
  // S1
  `1段落目のテキスト。文末は必ず句読点で終わる。\n2段落目のテキスト。`,
  // S2
  `...`,
];
```

- スライド1枚につき1エントリ（`NARRATIONS[i]` = スライド `i+1` 対応）
- 段落区切りは `\n`（改行1個）
- 文末は `。` `！` `？` のいずれかで終わること（TTS が文単位で合成する）
- 1段落 = 2〜4文程度が理想。長すぎると息継ぎが不自然になる。

---

## 尺の目安

| 指標 | 値 |
|------|-----|
| 実効読み上げ速度 | 約 6.7〜6.9 字/秒（1.1x 時） |
| 1エピソード目標 | 8〜10 分 |
| 必要文字数（目安） | 3,200〜4,150 字 |
| `TOTAL_SECS` 設定 | 700〜750 sec |
| スライド数 | 18 枚（EP02〜EP04 標準。1スライド1コンセプトで細分化） |

計算式：`推定秒数 = 総文字数 ÷ 6.8 + (段落数 × 0.45) + (文数 × 0.28)`

---

## VOICEVOX 訓読みルール

VOICEVOX は漢字を音読みしがちなため、文脈に合わせてひらがなに置き換える。

### 必須置換リスト

| 漢字表記 | 誤読 | 正しい読み | ひらがな置換後 |
|----------|------|-----------|--------------|
| 〜方（やり方・考え方・作り方・使われ方） | ほう | かた | 〜かた |
| すべての方 | ほう | かた（人・方法） | すべてのかた |
| 重なる | じゅうなる | かさなる | かさなる |
| 他の〜（ほかの〜） | た | ほか | ほかの〜 |
| 作り手・〜作り手から | しゅ（作りしゅ） | て | 作りて（作りてから） |
| 深掘り | ふかほり | ふかぼり | ふかぼり |

### 条件付き置換

| 漢字表記 | 置換条件 | 例 |
|----------|---------|-----|
| 方（かた） | 「人」「やり方」文脈 | すべてのかた、作りかた |
| 方（ほう） | 「一方」「方向」文脈 | **置換しない**（一方・方向・方針はそのまま） |
| 的（てき） | 接尾辞（具体的・客観的・効果的など） | **置換しない** |
| 的（まと） | ダーツの的・対象を指す場合 | まと（例：「まと全体」「まとの中心」） |

### スキャン用チェックポイント

ナレーション完成後、以下を必ずチェック：

```python
import re

checks = [
    (r'重なる', 'かさなる に置換'),
    (r'(?<![一方方向方針])方(?![向針法程])(?![をにはがもでのと])', '「かた」文脈か確認'),
    (r'他の', 'ほかの に置換'),
    (r'(?<!具体|客観|効果|積極|消極|相対|絶対|主観|戦略|論理|感情|一般|特定|直接|間接)的(?!に|な|だ)', '「まと」文脈か確認'),
    (r'作り手', '作りて に置換（しゅ誤読防止）'),
    (r'深掘り', 'ふかぼり に置換（ふかほり誤読防止）'),
    (r'と問うと、', '読点を除去 → と問うと（前の語と繋げる）'),
]
```

---

## スライド設計原則（Big Style）

モバイルで読める「大きいスタイル」を維持すること。Reference スタイル（小さい表）は使わない。

### フォントサイズ基準

```css
.t-xl { font-size: clamp(22px, 5.5cqw, 42px); }
.t-lg { font-size: clamp(18px, 4.2cqw, 34px); }
.t-md { font-size: clamp(15px, 3.5cqw, 28px); }
.t-sm { font-size: clamp(12px, 2.8cqw, 22px); }
```

`cqw` ベースで最小値を大きく設定する（`vw` ベース小さい値は NG）。

### コンポーネント早見表

| 用途 | コンポーネント | 備考 |
|------|--------------|------|
| メインタイトル | `.sh` + `.t-xl` | スライドの見出し |
| 本文テキスト | `.se` + `.t-md` | 説明文 |
| 2列比較 | `.duo` + `.pcard` | 左右に並べる |
| タグ列挙 | `.taglist` > `.tag` | キーワード強調 |
| フロー/矢印 | `.aflow` + `.achip` + `.aarrow` | ステップ説明 |
| バナー強調 | `.hl-banner` | 重要メッセージ |
| ボーダー行 | `border-left:6px solid + padding` | 3C事例などの行リスト |

### 1スライド1コンセプト

- 1枚のスライドで伝えることは1つ
- ナレーション1〜2段落に対応
- 視覚要素（テキスト・図）だけでも概要が伝わる構成にする
- ナレーションだけ聞いても理解できる構成にする

---

## 新規エピソード作成フロー

1. `_template/` をコピーして `01_beginner/epNN_<slug>/` を作成
2. `slide.html` に 18 枚分のスライド HTML を記述（big style CSS を流用）
3. `const NARRATIONS` を 18 エントリ作成（上記ルール適用）
4. VOICEVOX 訓読みスキャンを実施して修正
5. 動画生成：
   ```bash
   python3 _tools/video/make_video.py \
     01_beginner/epNN_<slug>/slide.html \
     --out 01_beginner/epNN_<slug>/video_build/out \
     --speaker 11 --speed 1.1 --final-outro 3.0
   ```
6. 出力確認：`video_build/out/epNN_<slug>_final.mp4`（目標 8〜10 分）

---

## 既存スライドを big style のまま細分化アップデートするフロー

既存エピソード（例：15枚）を **見た目のスタイルは変えずに** 18枚へ細分化し、
ナレーションも合わせて刷新する手順。EP02〜EP04 はこの方式で更新した。

### 大原則

- **CSS・base64フォント・JSエンジン・@keyframes は一切触らない**（巨大なので壊すと復旧が大変）
- 置き換えるのは2か所だけ：
  1. ステージ本体（`<div id="stage">` 〜 `</div><!-- /stage --></div><!-- /stage-wrap -->`）
  2. JSデータ配列（`const STEPS` 〜 `const TOTAL_SECS = N;`）
- フラッグシップ SVG 図（天秤・レーダー・ベン図など）と
  そのアニメーション（`epN-pulse` 等）は **元のまま流用**する

### 手順

1. **現状把握**：`grep -n 'id="s[0-9]"\|const NARRATIONS\|const SLIDES_META\|<!-- S[0-9]'` で
   スライド構成・JS配列の行番号を特定（ファイルは 1MB 超なので `Read` ではなく `sed`/`grep` で部分読み）
2. **細分化設計**：1スライド1コンセプトの原則で、内容の濃いスライドを分割して +N 枚にする。
   分割は「既存ナレーションの段落」を独立スライドに切り出すのが基本（新規執筆を最小化）
3. **フラッグシップ SVG を temp に退避**：`sed -n 'A,Bp' slide.html > /tmp/svg.html` で図ブロックを抽出し、そのまま再利用
4. **Python ビルドスクリプト**で機械的に再構築（手編集は事故のもと）：
   - 新しい 18枚分のステージ HTML を文字列で生成
   - `STEPS` / `SLIDES_META` / `NARRATIONS` / `TOTAL_SECS` をプログラムで生成
   - タイミングは各ナレーションの推定秒数（`chars/6.6 + paras*0.45 + sents*0.28`）から累積算出
   - `html.index()` で2ブロックを特定して splice → 上書き保存
5. **Playwright で検証**（必須）：
   ```python
   # JSエラー0件 + 全 STEPS.ids が DOM に存在することを確認
   missing = pg.evaluate("()=>{const m=[];STEPS.forEach(s=>s.ids.forEach(id=>{if(!document.getElementById(id))m.push(id)}));return m}")
   # sections / SLIDES_META / NARRATIONS / STEPS の件数一致も確認
   ```
   `missing == []` かつ section数 == SLIDES_META数 == NARRATIONS数 を確認
6. **VOICEVOX 訓読みスキャン**（上記チェックリスト）を実施
7. **コミット → 動画生成 → 出力確認**

### ステップ配置の慣習（STEPS の `t` 値）

- 各スライドの「見出し」は スライド開始時刻 `t=start`
- 続く要素は `start+0.5, start+1.0, …` と詰める
- 最後の「note（補足）」だけは `start + dur*0.35` あたりに遅らせて出す
- ※動画の実タイミングは make_video が音声長から再計算するため、STEPS はブラウザ確認用の概算でよい

### 番号表示の更新を忘れない

`<div class="slide-num">NN / 18</div>` と `dotContainerId:'sdN'`、`id="sN"` を
新しい総数・連番に合わせて全スライド振り直す（ビルドスクリプトで自動採番すると安全）。

---

## 実行環境の前提（コンテナ再起動後に必須）

コンテナが再起動すると VOICEVOX と Playwright が使えなくなることがある。動画生成前に確認：

```bash
# 1) VOICEVOX 起動確認（落ちていたら起動）
curl -s http://127.0.0.1:50021/version || \
  /opt/voicevox_engine/engine/linux-cpu-x64/run --host 127.0.0.1 --port 50021 &
# 起動待ち
until curl -s http://127.0.0.1:50021/version >/dev/null 2>&1; do sleep 2; done

# 2) Playwright ブラウザは PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers を指定して実行
PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers python3 _tools/video/make_video.py ...
```

- Playwright が「browser version mismatch（例 1194 vs 1223）」を出す場合は、
  既存の `/opt/pw-browsers/chromium-<旧>` を要求バージョン名で symlink して回避：
  ```bash
  ln -sf /opt/pw-browsers/chromium-1194 /opt/pw-browsers/chromium-1223
  mkdir -p /opt/pw-browsers/chromium_headless_shell-1223/chrome-headless-shell-linux64
  ln -sf /opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell \
    /opt/pw-browsers/chromium_headless_shell-1223/chrome-headless-shell-linux64/chrome-headless-shell
  ```
- ローカルリポジトリが古い（`_tools/` が消えている等）場合は
  `git pull origin claude/setup-marketing-course-dirs-GH2OH` で同期してから実行

---

## よくある問題と対処

| 問題 | 原因 | 対処 |
|------|------|------|
| 音声が途中で切れる | 文が句読点で終わっていない | ナレーション末尾に `。` を追加 |
| スライドが短すぎる | ナレーションが少ない | 1スライドあたり 150〜250 字を目安に追記 |
| 動画が長すぎる | ナレーションが多い | 1エピソード 3,200〜4,150 字に調整 |
| VOICEVOX 誤読 | 音読みデフォルト | 上記置換リストを適用 |
| スマホで文字が小さい | Reference スタイル（vw ベース）を使用 | Big style（cqw ベース）に差し替え |
| `ep2-pulse` などアニメーションが消える | slide.html 再構築時に CSS を削除 | 元ファイルから `@keyframes` ブロックをコピー（=ステージとJSのみ置換すれば起きない） |
| `VOICEVOX unreachable` | エンジン未起動（コンテナ再起動後） | `/opt/voicevox_engine/.../run` を起動して待機 |
| `playwright install` を促される/ブラウザ無し | バージョン不一致 | `/opt/pw-browsers` を symlink ＋ `PLAYWRIGHT_BROWSERS_PATH` 指定 |
| `make_video.py` が無い／`_tools` が消えている | ローカルが古い | `git pull` で remote と同期 |
| `Read` でファイルを開けない（1MB超） | base64フォントで巨大 | `sed`/`grep` で必要箇所だけ部分読み |
