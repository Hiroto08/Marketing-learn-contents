# SVGコンポーネント テンプレート ガイド

`_template/svg_components.html` — 動画スライド用の「動く図解」再利用パーツ集。
ブラウザで開くと12種のSVG図がスクロール／⟳ボタンでアニメーションします。

> 目的：文字で説明する代わりに **直感的に「形・動き・量」で伝える**。
> すべて 16:9・ダークテーマ・デザイントークン（`var(--accent)` 等）連動なので、各EPのアクセント色に自動追従します。

---

## 収録コンポーネント（12種）

| # | 名前 | タグ | 用途の例 | 主な技法 |
|---|------|------|----------|----------|
| 1 | カスタマージャーニー | `path` | 接点設計・段階遷移 | `offset-path` でマーカー走行＋`stroke-dashoffset` 描画 |
| 2 | コンバージョンファネル | `funnel` | 訪問→購入の歩留まり | 台形 `polygon` を `scaleY` で順次出現 |
| 3 | スコアゲージ | `gauge` | 健全度・達成度 | 半円アーク `dasharray`＋針 `rotate` |
| 4 | 構成比ドーナツ | `donut` | 流入チャネル比率 | 円 `dasharray` セグメント |
| 5 | 成長バーチャート | `bars` | 売上・KPIの推移 | `rect` を `scaleY` で成長 |
| 6 | A/Bトレンド | `line` | テスト結果の逆転 | 2本の線を `dashoffset` で描画 |
| 7 | プロセスフロー | `flow` | PDCA・手順 | ノード＋流れる破線コネクタ |
| 8 | 価値の天秤 | `scale` | 価格 vs 価値 | 梁を `rotate` で傾ける |
| 9 | ポジショニングマップ | `matrix` | 競合の空白地帯 | 2×2軸＋プロット＋パルス強調 |
| 10 | KPIリング | `ring` | 多指標ダッシュボード | 同心円 `dasharray` |
| 11 | レーダーチャート | `radar` | 強み・弱みの形 | 五角形 `polygon` をスケール |
| 12 | 指標カード | `stat` | 大きな数字の訴求 | JSカウントアップ＋アイコン |

---

## 本番スライドへの組み込み手順

1. `svg_components.html` をブラウザで開き、使いたい図を決める。
2. その `<svg>…</svg>` を `content_epNN.py` の該当スライドへ貼る。
3. アニメさせたい要素に **`class="se"` と一意な `id`** を付ける（既存リビールエンジン対象）。
4. `STEPS` に `{si:<スライド番号-1>, t:<秒>, ids:['その id'], anim:'rv-up'}` を追加。
5. 組み立て＆検証：
   ```bash
   python3 /tmp/verify-slides/assemble.py /tmp/verify-slides/content_epNN.py <出力先 slide.html>
   node /tmp/verify-slides/verify-one.js     <出力先>   # エラー0 / 最終スライド到達
   node /tmp/verify-slides/scan-overflow.js  <出力先>   # BAD_COUNT 0（16:9から溢れない）
   node /tmp/verify-slides/measure-fonts.js  <出力先>   # SMALL（26px未満）が出ない
   ```

### 貼り付け時の約束ごと
- **viewBox は `0 0 400 225`（=16:9）** に揃える。スライドの `.pad` 内で `width:min(78%,640px)` 程度に。
- 図中テキストは **font-size 26px 相当以上**（viewBox基準なら `font-size="13"` 前後＝レンダリングで26px超）。補足ラベルは最小24px。
- 色は **必ずトークン**（`var(--accent)/--acc2/--blue/--green/...`）で指定。生のhexを足さない＝3色ルール維持。
- 重い情報は上部に。**下部約1/4はセーフゾーン**として空ける（YouTubeシークバー／スマホUI回避）。

---

## アニメーション・プリミティブ（CSSクラス）

`svg_components.html` 内の `<style>` に定義。`.stage` に `.play` が付くと発火します。
本番スライドでは代わりに `class="se"` ＋ `rv-*`（`rv-up/rv-fade/rv-scale/rv-pop/...`）を使ってください。

| クラス | 効果 | 使う属性 |
|--------|------|----------|
| `.draw` | 線を描き進める | `style="--len:<線長>"` |
| `.sweep` | アーク／円弧を伸ばす | `style="--len:.. ;--to:.."` |
| `.grow` | 下から伸びる | `transform-box:fill-box` |
| `.pop` | ポンと出現 | — |
| `.fup` | 下からフェード | — |
| `.flow` | 破線が流れ続ける | `stroke-dasharray` |
| `.travel` | パスに沿って走る | `offset-path:path(...)` |
| `.pulse` | 半径が脈動 | `style="--r0:..;--r1:.."` |
| `.needle` | 角度を回す | `style="--ox/--oy/--from/--deg"` |
| `.d1`〜`.d8` | 発火を段階遅延 | — |

`--len`（線長・円周）は概算で良い。円周 = `2 × π × r`、半円アーク = `π × r`。

---

## カスタマイズ早見表
- **数値を変える**：`<text>` の中身と、対応する `--to`/`dasharray`/座標を調整。
- **段数を増やす**：ファネル／バーは `polygon`/`rect` を追加し `d5,d6...` を付与。
- **色テーマ**：EP_CSS の `:root{--accent:#XXXX}` を変えるだけで全図が追従。
- **動きを止めたい**：`prefers-reduced-motion` で自動停止済み（アクセシビリティ対応）。
