<!--
このファイルは note 下書き保存の「唯一の真実源」（YouTube側の docs/upload-status.md 相当）。
週次noteジョブ（Routine）はこの表を読み、status が「校了・下書き未保存」の先頭1本だけを
note に下書き（非公開）として保存し、成功したら status を「下書き保存済み」に更新して
note_id / edit_url / saved_at を書き戻す。**公開は常に人間**（post_note_api.py に公開処理は無い）。

status の意味：
- 生成のまま（校了前）  … make_note_article.py の下書きのまま。動画口語が残る。**保存対象外**。
                          note-production スキルの編集ロールで校了させると「校了・下書き未保存」へ。
- 校了・下書き未保存    … 編集パイプライン通過＋verify_note.py PASS。**次にジョブが保存する対象**。
- 下書き保存済み        … note に下書き保存済み（非公開）。note_id / edit_url を記録。

手動で校了させたら、その回の status を「校了・下書き未保存」に手で書き換えること。
-->

# note 下書き保存 状態表

| EP | ファイル | status | note_id | edit_url | saved_at |
|----|---------|--------|---------|----------|----------|
| EP01 | ep01_what-is-marketing.md | 下書き保存済み | 171461571 | https://editor.note.com/notes/171461571/edit | 2026-07-24 |
| EP02 | ep02_3c-stp-analysis.md | 下書き保存済み | 171462924 | https://editor.note.com/notes/171462924/edit | 2026-07-24 |
| EP03 | ep03_persona-pitfalls.md | 下書き保存済み | 171462928 | https://editor.note.com/notes/171462928/edit | 2026-07-24 |
| EP04 | ep04_benefit-vs-feature.md | 下書き保存済み | 171462932 | https://editor.note.com/notes/171462932/edit | 2026-07-24 |
| EP05 | ep05_customer-journey.md | 下書き保存済み | 171462935 | https://editor.note.com/notes/171462935/edit | 2026-07-24 |
| EP06 | ep06_pricing-psychology.md | 下書き保存済み | 171462938 | https://editor.note.com/notes/171462938/edit | 2026-07-24 |
| EP07 | ep07_4p-4c-mix.md | 下書き保存済み | 171960790 | https://editor.note.com/notes/171960790/edit | 2026-07-27 |
| EP08 | ep08_usp-differentiation.md | 下書き保存済み | 172111882 | https://editor.note.com/notes/172111882/edit | 2026-07-28 |
| EP09 | ep09_cpa-ltv.md | 下書き保存済み | 174283548 | https://editor.note.com/notes/174283548/edit | 2026-08-11 |
| EP10 | ep10_copywriting-5laws.md | 生成のまま（校了前） | - | - | - |
| EP11 | ep11_sns-engagement.md | 生成のまま（校了前） | - | - | - |
| EP12 | ep12_ab-testing.md | 生成のまま（校了前） | - | - | - |
| EP13 | ep13_ai-market-research.md | 生成のまま（校了前） | - | - | - |
| EP14 | ep14_ai-content-creation.md | 生成のまま（校了前） | - | - | - |
| EP15 | ep15_ai-data-analysis.md | 生成のまま（校了前） | - | - | - |
| EP16 | ep16_ai-chatbot.md | 生成のまま（校了前） | - | - | - |
| EP17 | ep17_brand-equity.md | 生成のまま（校了前） | - | - | - |
| EP18 | ep18_ltv-crm-strategy.md | 生成のまま（校了前） | - | - | - |
| EP19 | ep19_marketing-org.md | 生成のまま（校了前） | - | - | - |
| EP20 | ep20_growth-hack.md | 生成のまま（校了前） | - | - | - |

<!--
運用メモ：
- 現在「校了・下書き未保存」は0本。EP10以降を校了させるまで、週次noteジョブは「保存対象なし」で
  安全に停止する（未校了記事は投稿しない）。
- EP10以降を校了させるには note-production スキル（リライト→パッケージ→校正→QA）を回す。
  校了できたら該当行を「校了・下書き未保存」に更新 → 次の火曜ジョブが自動で下書き保存する。
-->
