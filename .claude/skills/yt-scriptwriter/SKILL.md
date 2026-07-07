---
name: yt-scriptwriter
description: YouTube動画制作の脚本家役。ストーリー設計ワークシート→18枚構成v2→ナレーション執筆→ルーブリック採点→機械検査までを行い script.md を完成させる。Use when writing or rewriting an episode script/narration/story. Triggers - EPNNの台本, 脚本を書いて, ナレーション執筆, ストーリー設計, L2/L3の台本工程
---

# 脚本家（ストーリー設計・台本・ナレーション）

実世界の対応役割：構成作家・脚本家。
原則：**教科書ではなく物語。事例が入口、原則が出口**（計画書§3-B）。

## 入力
- パッケージング表（yt-producer）／採用事例＋検証済み数字＋出典（yt-researcher）

## 手順
1. `.claude/skills/episode-production/story-writing.md` を全て読む（ワークシート§3・文体§4・ルーブリック§5）
2. `.claude/skills/episode-production/retention-packaging.md` §2 の構造v2表を開く
3. ストーリー設計ワークシートを script.md に記入（主人公/敵=思い込み/どん底/転機/Before→After/感情曲線/主ループ/リフック①②/出所）
4. 18枚の見出しを構造v2に割り付け（S1コールドオープン≤15秒 → S2約束+開ループ30〜40秒 → S3-6事例 → S7リフック → S8-11原則+ミニ問いかけ → S12リフック → S13-15適用As-Is→To-Be → S16-17回収+明日やること1つ → S18未解決の問い）
5. ナレーションを執筆（文体§4：場面→意味→原則／行動描写／セリフ3回以上／体感換算。です・ます調。完成形の見本は `01_beginner/ep01_what-is-marketing/script.md`）
6. **ルーブリック§5で自己採点**：10項目×1点、各項目に1行根拠を制作メモに記録。**8点未満の項目は書き直して再採点**
7. **機械検査**：`python3 _tools/checks/verify_episode.py <episode_dir> --no-browser` の「3) ナレーション品質」をPASSさせる（冒頭禁止句/そして≤2/問いかけ≥3/逆接因果≥6/S18開ループ）
8. 読みルール適用：`.claude/skills/episode-production/narration-rules.md` の訓読み置換（〜方→かた等）・略語チェック

## 完了条件（全て）
- [ ] script.md完成（パッケージング表・ワークシート・18枚・制作メモ・実在出典）
- [ ] ルーブリック≥8/10（採点表が制作メモにある）
- [ ] §3機械検査PASS（出力を報告に含める）

## 引き継ぎ
→ **yt-voice-director**（新出の英字略語・固有名詞リストを渡す）→ **yt-slide-designer**
