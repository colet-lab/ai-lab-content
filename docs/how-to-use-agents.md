# エージェント使い方

各エージェントの呼び出し方・入力例・出力の使い方。

---

## 基本の流れ

```
① でぐさんがネタを決める（手動 or article-planner提案）
  ↓
② でぐさんが実作業・動画撮影（この作業フォルダで実施）
  ↓ 会話履歴・スクショ・experiments/ が自動で残る
  ↓
③ article-writer で記事生成
  ↓
④ youtube-producer で動画メタデータ・台本生成（撮影前に戻ってもOK）
  ↓
⑤ resource-maker で配布資料生成
  ↓
⑥ でぐさんが推敲・DEGU追記
  ↓
⑦ publisher で WP下書き投稿
  ↓
⑧ でぐさんが WordPress 管理画面で最終確認・公開
  ↓
⑨ sns-composer で SNS 投稿文案生成
  ↓
⑩ 社内スタッフが SNS に投稿
```

---

## 1. article-planner（ネタ提案）

### 呼び方
```
plan 5本提案して
plan Claude Code deny系で3本
plan 最新のセキュリティ話題で2本
```

### 例
**入力：**
```
plan 3本。セキュリティ寄りで、経営者ターゲット
```

**期待される応答：**
article-queue.csv に3行追加 + 会話上で以下のサマリー報告

```
ネタ提案3本:
1. Claude Codeの.envを読ませないための最小設定（セキュリティ診断型）
2. 社員が個人ChatGPTを使ってる問題、どう検知するか（シャドーAI型）
3. 「AIで作ってみた」Webアプリ、5分で崩壊する事例集（Vibe coding批判型）
```

### 使うタイミング
- 週の始めにまとめて5〜10本出してストック
- 突発的に「今週あと1本何書こう」の時

---

## 2. youtube-producer（動画企画）

### 呼び方
```
video <テーマ or article-queue.csvの行番号>
```

### 例
**入力：**
```
video Claude Codeの.env事故を防ぐ90ルール
```

**期待される応答：**
タイトル3案、サムネ案、冒頭30秒台本、本編の流れ、チャプター、説明文、Shorts候補3本を出力。

### 使うタイミング
- 撮影前日or当日朝
- 撮影後にメタデータだけ必要な場合

---

## 3. article-writer（記事下書き生成）

### 呼び方
```
draft <テーマ or article-queue.csvの行番号>
```

### 例
**入力：**
```
draft Claude Codeの.env事故を防ぐ90ルール
関連: experiments/20260418_claude-deny/
撮影済み: YES（台本は docs/drafts/20260418_video_script.md 参照）
```

**期待される応答：**
`drafts/20260418_claude-deny-90.md` に Markdown 記事を生成。DEGU 追記箇所あり。

### 使うタイミング
- 実作業＋動画撮影が終わった後
- 事例の土台ができた段階

---

## 4. resource-maker（配布資料生成）

### 呼び方
```
resource <テーマ or article-queue.csvの行番号>
```

### 例
**入力：**
```
resource Claude Codeの.env事故を防ぐ90ルール
記事: drafts/20260418_claude-deny-90.md
動画: 撮影済み
```

**期待される応答：**
`drafts/resources/20260418_claude-deny-90.md` に資料を生成。

### 使うタイミング
- 記事生成と同時か後
- 撮影前に作って撮影台本として使うことも可

---

## 5. publisher（WP下書き投稿）

### 呼び方
```
publish <slug>
publish resource <slug>
```

### 例
**記事を投稿：**
```
publish 20260418_claude-deny-90
```

**資料を投稿：**
```
publish resource 20260418_claude-deny-90
```

**期待される応答：**
- Markdown → SWELL HTML変換
- 画像を WordPress メディアへアップロード
- 下書きとして投稿
- 投稿URLを返す
- drafts/ → published/ へファイル移動

### 使うタイミング
- でぐさんが推敲・DEGU追記を終えた後

---

## 6. sns-composer（SNS投稿文案）

### 呼び方
```
sns <slug or 公開URL>
```

### 例
**入力：**
```
sns 20260418_claude-deny-90
```

**期待される応答：**
- X：投稿案5本
- Threads：投稿案2本 + 返信候補3本
- Instagram Reels：キャプション案

### 使うタイミング
- 記事・動画を公開した後

---

## 補助コマンド

### 記事一覧
```
list
```
drafts/ と published/ の一覧をステータス付き表示。

### article-queue.csv を見る
```
queue
```
ネタスプレッドシートの内容を表示。

### 今月のパスワード設定（ラボの棚）
```
password <新しいパスワード>
```
resource CPT の全ページのパスワードを一括更新（WP-CLI スクリプト）。

---

## 典型的な1週間の流れ

### 月曜
1. でぐ: スクショ撮りながら Claude Code で実験
2. でぐ: `draft <テーマ>` で記事生成
3. でぐ: 推敲・DEGU追記
4. でぐ: `publish <slug>` で WP下書き
5. でぐ: WordPress 管理画面で最終確認 → 公開
6. でぐ: `sns <slug>` で SNS 投稿文案生成
7. 社内スタッフ: X に投稿開始

### 火曜
1. でぐ: `video <テーマ>` で動画台本・タイトル案を得る
2. でぐ: 撮影（DJIマイク + 一眼 + OBS）
3. でぐ: 社内スタッフに編集依頼

### 水曜
1. 社内スタッフ: 動画編集仕上げ
2. でぐ: YouTube に本編アップロード
3. でぐ: Shorts も切り抜いて投稿

### 木曜
1. でぐ: `plan 3本` で次週のネタ提案を得る
2. でぐ: 次のテーマの実作業開始

### 金曜
1. でぐ: 新規記事 `draft` → `publish`
2. 週次振り返り（KPIダッシュボード確認）
