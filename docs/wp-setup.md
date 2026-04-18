# WordPress 側の設定手順

でぐさんが WordPress 管理画面で実施する作業の手順書。

## 前提

- colet-lab.jp は WordPress + SWELL テーマ
- 既にコラムのカテゴリ構造あり

## 1. カスタム投稿タイプの作成

### プラグイン: Custom Post Type UI

1. プラグインインストール：Custom Post Type UI
2. 有効化

### 作成する CPT は2つ

#### 1-1. ai-lab（記事用）

| 項目 | 値 |
|---|---|
| Post Type Slug | `ai-lab` |
| Plural Label | AIに詳しい必要はない |
| Singular Label | 記事 |
| Menu Position | 適宜 |
| Show in REST API | **true**（publisher が使う） |
| Supports | title, editor, thumbnail, excerpt, custom-fields |
| Taxonomies | post_tag（タグ）、category（カテゴリ、将来用） |
| Rewrite Slug | `ai-lab`（URL：/ai-lab/xxx/）|

#### 1-2. resource（資料用）

| 項目 | 値 |
|---|---|
| Post Type Slug | `resource` |
| Plural Label | 資料 |
| Singular Label | 資料 |
| Menu Position | 適宜 |
| Show in REST API | **true** |
| Supports | title, editor, thumbnail, excerpt, custom-fields |
| Taxonomies | post_tag（タグ）、resource_category（後述） |
| Rewrite Slug | `resource`（URL：/resource/xxx/）|

## 2. 固定ページ「ラボの棚」の作成

1. 管理画面 > 固定ページ > 新規追加
2. タイトル：**ラボの棚**
3. スラッグ：`resources`（URL: /resources/）
4. パスワード保護：月次パスワード（初月から運用）
5. 本文：以下の構成（SWELLブロック使用）

### ページ構成

```
📚 ラボの棚

━━━━━━━━━━━━━━━━━━━━━━
🎯 まず手に取るべき3つ
━━━━━━━━━━━━━━━━━━━━━━
[SWELL投稿リストブロック：resource CPT の特定タグ「おすすめ」のもの]

━━━━━━━━━━━━━━━━━━━━━━
🆕 最近追加されたもの
━━━━━━━━━━━━━━━━━━━━━━
[SWELL投稿リストブロック：resource CPT の新着順]

━━━━━━━━━━━━━━━━━━━━━━
📂 カテゴリ別
━━━━━━━━━━━━━━━━━━━━━━
（資料が増えてから記載）
```

## 3. 固定ページ「AIに詳しい必要はない とは」の作成

1. 固定ページ > 新規追加
2. タイトル：**AIに詳しい必要はない とは**
3. スラッグ：`about`（URL: /about/）
4. 本文：`drafts/20260416_note-guide.md` の内容をベースに作成

## 4. WPForms の設置

### プラグイン
- WPForms Lite（無料）または WPForms Pro

### 問い合わせフォーム（重めの項目）

| 項目 | 必須 |
|---|---|
| 会社名 | 必須 |
| 氏名 | 必須 |
| 電話番号 | 必須 |
| メールアドレス | 必須 |
| 業種 | 必須（選択肢） |
| 相談内容 | 必須（長文） |
| どこで知ったか | 任意 |

### 自動返信メール

送信後、自動で以下を返信：

```
件名: お問い合わせありがとうございます（コレットラボ）

{{会社名}} {{氏名}} 様

お問い合わせありがとうございます。
内容を確認次第、2営業日以内にご返信いたします。

併せて、ラボの棚（資料集）のパスワードをお送りします：

パスワード: {{今月のパスワード}}
資料室URL: https://colet-lab.jp/resources/

よろしくお願いいたします。

---
株式会社コレットラボ
出口宣佳（でぐ）
```

### 管理者通知メール

でぐさんに新規問い合わせを即時通知。

## 5. ラボの棚のパスワード一括設定

### WP-CLI スクリプト（publisher エージェントが自動実行）

月初に以下のコマンドで全 resource CPT ＋ 固定ページ「ラボの棚」のパスワードを一括更新：

```bash
#!/bin/bash
# monthly_password_update.sh

NEW_PASSWORD="colet-lab-2605"  # 引数で受け取る

# 固定ページ「ラボの棚」更新
wp post update $(wp post list --post_type=page --name=resources --field=ID) \
  --post_password="$NEW_PASSWORD"

# resource CPT 全更新
for id in $(wp post list --post_type=resource --field=ID); do
  wp post update $id --post_password="$NEW_PASSWORD"
done

echo "パスワードを $NEW_PASSWORD に更新しました"
```

## 6. SEO SIMPLE PACK の確認

- インストール済み（wp-auto-publish が使用中）
- メタディスクリプション自動設定機能を publisher が使うので、動作確認

## 7. SWELL の設定

### カスタマイズ > 投稿・固定ページ設定
- 目次を自動生成する：**ON**
- 著者情報を表示：ON

### 著者プロフィール（管理画面 > ユーザー > 出口宣佳）
- 表示名：でぐ（出口宣佳）
- プロフィール：コレットラボ代表。プロモーション全領域20年。
- リンク：X / Threads / LINE公式 / YouTube

## 作業チェックリスト

- [ ] Custom Post Type UI プラグインインストール
- [ ] CPT `ai-lab` 作成
- [ ] CPT `resource` 作成
- [ ] 固定ページ「ラボの棚」作成＋SWELL投稿リストブロック配置
- [ ] 固定ページ「AIに詳しい必要はない とは」作成
- [ ] WPForms プラグインインストール＋問い合わせフォーム設置
- [ ] 自動返信メール設定
- [ ] 管理者通知メール設定
- [ ] SWELL投稿者プロフィール更新
- [ ] ラボの棚の初月パスワード設定
