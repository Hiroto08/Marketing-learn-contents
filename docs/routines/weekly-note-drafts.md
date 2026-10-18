# 週次 note 下書きジョブ（毎週火 9:00 JST ／ cron `0 0 * * 2`）

```
週次note自動化ジョブ（note編集デスク）。次の2話ぶんのnote記事を「校了→見出し画像生成→下書き（非公開）保存」まで自動で仕上げる。公開はこのジョブではしない（毎日公開ジョブが行う）。

【基点】git fetch origin && git checkout -B note-weekly origin/<基点ブランチ>。_deliverables/note/note-draft-status.md が無ければ何もせず報告して停止。
【認証】環境変数 _note_session_v5 を NOTE_COOKIE="_note_session_v5=${_note_session_v5}" の形で渡す。Cookie値は絶対に表示・ログ出力しない。
【対象】note-draft-status.md で status が「下書き保存済み」「公開済み」でない行のうち、_deliverables/note/ep<NN>_*.md が実在するEP番号の小さい順に最大2つ（無ければ python3 _tools/repurpose/make_note_article.py --episode <dir> で元原稿を作り、状態表に「生成のまま（校了前）」で行を足す）。1話ずつ順に行い、1話目がFAILしたら止める。
1. 校了：note-production スキルで 4ロール（note-writer → note-packager → note-proofreader → note-qa）を回し、python3 _tools/checks/verify_note.py <file> が RESULT: PASS になるまで。数字・固有名詞は <ep_dir>/script.md と一致させる。YouTube への導線は記事に手書きしない（公開時に note_cta.py が自動で入れる）。
2. 見出し画像：python3 _tools/publish/make_note_thumbnail.py --file <file> → _deliverables/note/thumbnails/ep<NN>.png。文字切れを目視確認。
3. 下書き保存：python3 _tools/publish/post_note_api.py --file <file> --dry-run → 問題なければ dry-run なしで実行。note_id と編集URLを控える。
4. note-draft-status.md を「下書き保存済み」に更新（note_id / edit_url / saved_at）→ コミット → git push origin HEAD:<基点ブランチ>（拒否なら作業ブランチへ push -u）。
401/403 が続くときは Cookie 期限切れとして「環境変数 _note_session_v5 の更新が必要」とだけ報告して停止。エンドポイントを推測で変えない。
報告：処理したEP・タイトル・verify_note結果・note_id・編集URL・見出し画像パス。
```
