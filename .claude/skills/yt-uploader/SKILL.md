---
name: yt-uploader
description: YouTube配信オペレーター役。完成した本編/Shortsを非公開(private)でYouTubeへ自動アップロードし、タイトル・概要欄・タグ・サムネ・プレイリスト・公開予約まで「公開ボタンを押すだけ」の状態に整える。Use when uploading built videos to YouTube or preparing scheduled publishing. Triggers - アップロードして, YouTubeに上げて, 非公開で上げて, 公開予約
---

# YouTube配信オペレーター（自動アップロード）

実世界の対応役割：テレビ局の送出オペレーター。
原則：**アップロードは常に private で行い、人間が Studio で最終確認してから公開する。秘密情報（トークン類）はリポジトリ・チャット・コミットに絶対に置かない。**

## 初回セットアップ（ユーザーが手元PCで1回だけ）

1. Google Cloud Console → プロジェクト作成 → **YouTube Data API v3** を有効化
2. OAuth同意画面（外部・テスト）→ テストユーザーに自分を追加
3. 認証情報 → OAuthクライアントID（**デスクトップアプリ**）作成
4. 手元PCで `python3 _tools/publish/get_refresh_token.py <CLIENT_ID> <CLIENT_SECRET>`
   → ブラウザ認可 → 表示された3値を **claude.ai/code の環境設定 > Secrets** に登録：
   `YT_CLIENT_ID` / `YT_CLIENT_SECRET` / `YT_REFRESH_TOKEN`

## 入力

- ビルド済み mp4（`video_build/*_final.mp4` / `shorts_build/short*/short*_final.mp4`）
- `description.md`（本編メタデータ源）／`shorts.md`（Shortsタイトル源）

## 手順

1. **QA通過を確認**してから実行（verify_episode / verify_shorts がPASSしていない動画は上げない）
2. まず `--dry-run` でメタデータ組み立てを確認：
   ```bash
   python3 _tools/publish/upload_youtube.py --episode <ep_dir> --dry-run
   python3 _tools/publish/upload_youtube.py --shorts  <ep_dir> --dry-run
   ```
   タイトル100字以内・説明5000字以内・タグは自動で切り詰められる
3. 本番実行（既定 private。公開予約は `--publish-at 2026-07-20T21:00:00+09:00`）：
   ```bash
   python3 _tools/publish/upload_youtube.py --episode <ep_dir> \
     --thumbnail <png> --playlist <playlistId> \
     --pin-comment "本編はこちら→（後でStudioでピン留め）"
   python3 _tools/publish/upload_youtube.py --shorts <ep_dir>
   ```
4. 出力された Studio URL と `publish_manifest.json`（videoId・SHA-256）を確認。
   **同一ハッシュは自動スキップ**されるので再実行は安全
5. スクリプト末尾の「残る手動作業」チェックリストをそのままユーザーに渡す

## APIで自動化できないもの（must: ユーザーへ明示）

- **Shortsの「関連動画」リンク**（送客の本命導線。Studio → Short → 関連動画で手動設定）
- **固定コメントのピン留め**（コメント投稿までは自動、ピン留めはStudio）
- エンドスクリーン・カード

## クォータ・制約

- videos.insert=1600単位／thumbnails.set=50／playlistItems.insert=50。
  既定1日10,000単位 ≒ **動画6本/日**（本編1+Shorts3の1話ぶんで約5,000単位）
- OAuth同意画面が「テスト」のままだとリフレッシュトークンは**7日で失効**
  → 運用に乗せる時は同意画面を「本番」に押し上げる（審査は youtube.upload スコープのみなら軽い）
- アップロード先はトークンのGoogleアカウントのチャンネル。ブランドアカウントの場合は
  認可時にそのチャンネルを選ぶこと

## 完了条件

- [ ] 全動画が private で Studio に並び、タイトル/概要欄/タグが description.md と一致
- [ ] publish_manifest.json に videoId が記録されている
- [ ] 手動作業チェックリストをユーザーに提示済み

## 引き継ぎ

← **yt-video-editor / yt-shorts-video-editor**（ビルド済みmp4を受け取る）
→ ユーザー（Studioで最終確認 → 公開 or 公開予約の確定）→ 公開後 **yt-analyst**
