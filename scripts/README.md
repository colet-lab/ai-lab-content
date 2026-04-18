# scripts/

publisher 実装と運用スクリプト。

## ファイル一覧

| ファイル | 用途 |
|---|---|
| `publish.py` | Markdown → SWELL HTML 変換 + WordPress下書き投稿 |
| `requirements.txt` | Python依存パッケージ |
| `update_resource_password.sh` | ラボの棚の月次パスワード一括更新（WP-CLI） |

## セットアップ手順

### 1. Python依存をインストール

```bash
cd ~/claude/note-content
python3 -m venv venv
source venv/bin/activate
pip install -r scripts/requirements.txt
```

### 2. .env ファイルを作成

プロジェクトルート（`note-content/` 直下）に `.env` ファイルを作成し、以下を記載：

```
WP_BASE_URL=https://colet-lab.jp
WP_USERNAME=your-wp-admin-username
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx

WP_CPT_ARTICLE=ai-lab
WP_CPT_RESOURCE=resource

RESOURCE_PASSWORD=colet-lab-2604
```

`.env` は `.gitignore` で除外されており、Git にはコミットされません。

### 3. WordPress Application Password の発行

1. WordPress 管理画面にログイン
2. ユーザー > プロフィール
3. 下部の「アプリケーションパスワード」セクション
4. 名前欄に `note-content-publisher` と入力 → 新しいアプリケーションパスワードを追加
5. 表示されたパスワード（`xxxx xxxx xxxx xxxx xxxx xxxx` 形式）を `.env` の `WP_APP_PASSWORD` に貼り付け

### 4. カスタム投稿タイプの REST API 有効化確認

WordPress 側で `ai-lab` と `resource` のカスタム投稿タイプを作成する際、
**Show in REST: true** が必須（Custom Post Type UI プラグインで有効化可能）。

REST API base name は以下がデフォルト（必要に応じて .env で変更）：
- `ai-lab` → `WP_CPT_ARTICLE=ai-lab`
- `resource` → `WP_CPT_RESOURCE=resource`

## 使い方

### 記事を下書き投稿

```bash
python3 scripts/publish.py 20260418_claude-deny-90
```

指定したスラッグを含む Markdown ファイルを `drafts/` 配下から探して投稿。

### 資料を下書き投稿

```bash
python3 scripts/publish.py --resource 20260418_mcp-setup
```

`drafts/resources/` 配下から探す。resource CPT として投稿、パスワード保護が付く。

### 変換結果だけ確認（投稿しない）

```bash
python3 scripts/publish.py 20260418_claude-deny-90 --dry-run
```

WordPress には接続せず、Markdown → HTML 変換の結果を表示。

### ラボの棚の月次パスワード一括更新

```bash
bash scripts/update_resource_password.sh colet-lab-2605
```

※ このスクリプトは WP-CLI がサーバー側で実行可能な環境を前提にしています。
SSH 経由または WordPress サーバー上で実行してください。
ローカルから実行する場合は、WordPress管理画面で手動更新してください。

## トラブルシューティング

### `.env が見つかりません` と出る

プロジェクトルート（CLAUDE.md と同じ階層）に `.env` を作成してください。

### 画像アップロードが失敗する

- 画像ファイルが `screenshots/` 配下に存在するか確認
- Markdown 内のパスが `![](screenshots/xxx.png)` の形式か確認
- WordPress のアップロードサイズ上限を確認

### `必須マーカー 'TITLE' が見つかりません`

Markdown ファイルの冒頭に `===TITLE===`, `===SLUG===`, `===META===`, `===BODY===` が
単独の行で記載されているか確認してください。

### カスタム投稿タイプが見つからない（404エラー）

WordPress 側で CPT が REST API 有効で作成されているか確認。
Custom Post Type UI プラグインの設定で「Show in REST」を true に。

### 公開されてしまった

`publish.py` は `post_status=draft` で投稿します。公開は WordPress 管理画面で手動で行う設計です。
万が一公開されてしまった場合は、コード内で `post_status` を確認してください。

## セキュリティ注意

- `.env` ファイルは絶対に Git にコミットしない（`.gitignore` で除外済）
- Application Password は漏洩したら即座に WordPress 管理画面から削除
- 本番環境の投稿は必ず `--dry-run` で動作確認してから実行することを推奨
