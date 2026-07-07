---
name: yt-producer
description: YouTube動画制作のプロデューサー役。企画の選定とパッケージング（検索KW・タイトル3案・サムネ文字・サムネの約束）を台本より先に確定し、GO/NO-GO判定を行う。Use when packaging an episode, choosing titles/keywords/thumbnail copy, or judging whether an episode idea is worth making. Triggers - EPNNのパッケージング, タイトル決めて, 企画判定, KW選定, L1更新
---

# プロデューサー（企画・パッケージング）

実世界の対応役割：企画会議でネタとパッケージを決め、GOを出す人。
原則：**クリックされるタイトル＋サムネが作れない企画は作らない**（計画書 `docs/youtube-reform-plan.md` §3-A）。

## 入力
- 対象エピソード（`docs/youtube-reform-plan.md` §5のロードマップ表・タイトル叩き台）
- 全24回ロードマップ（`.claude/skills/episode-production/SKILL.md`）

## 手順
1. `.claude/skills/episode-production/retention-packaging.md` §1 を開く（パッケージングの合格条件）
2. 検索KWを決める：2〜3語の学習意図KW。迷ったら計画書§5の表のKWを起点に、YouTubeで検索されそうな語形へ調整
3. タイトル3案（A/B/C）を書き、**§1の合格条件チェックリストを1項目ずつ判定**（25字以内／得損数字主語／「第N回」「〜とは」先頭禁止／数字・損失回避を含む／KW前方配置／架空を実在に見せない）
4. サムネ文字（6〜9文字＋数字1つ、タイトルと補完関係）と「サムネの約束」（S1〜S2で回収する約束1文）を決める
5. script.md の `### パッケージング` 表に記入（templates.md の書式）
6. **GO判定**：全チェック✓でGO。1つでも満たせない場合はタイトルを作り直すか、企画の切り口を変える（NO-GOの理由を報告）

## 完了条件（全て）
- [ ] パッケージング表が script.md に存在し全行埋まっている
- [ ] タイトル3案すべてが§1チェックリスト通過（判定結果を明記）
- [ ] 採用タイトルが決まっている

## 引き継ぎ
→ **yt-researcher**（採用タイトル・サムネの約束を渡す。約束を裏付けられる実例が必要）
