# エージェント仕様

6つのエージェントの詳細仕様。呼び出し方は [how-to-use-agents.md](how-to-use-agents.md) 参照。

## 1. article-planner

### 役割
ネタを動的に提案。「〇〇設定できてる？」「こんなの作ってみない？」型で、でぐさんの実験・体験ベースになりうるテーマを投げる。

### インプット
- 指示（例：「5本提案」「Claude Code deny系で3本」）
- `article-queue.csv`（重複回避用）
- `drafts/`, `published/` 配下のファイル一覧
- CLAUDE.md の柱・方針
- 任意：WebSearch（セキュリティ・法人向け新機能など、法人利用に直結する情報のみ）

### アウトプット
`article-queue.csv` に新規行を追加＋会話上でサマリー報告。

```csv
提案日, タイトル, 柱, キーワード, ターゲット, ステータス, 関連動画, 関連資料, 備考
```

### ネタ提案の型（7パターン）
| 型 | 例 |
|---|---|
| 診断型（設定できてる？） | Claude Codeのdeny、Gemini学習設定 |
| 発見型（これ知ってる？） | Claude Plan Mode、OpenAI Codex連携、NotebookLM |
| やらかし型 | AIに〇〇させて事故った話 |
| Vibe coding批判型 | 「作ってみた」アプリのセキュリティ5分解析 |
| シャドーAI型 | 社員が個人ChatGPTに顧客名貼る問題 |
| Tips型（3社別） | Claude/GPT/Gemini の便利機能 |
| 実験提案型 | こんなの試してみない？ |

### 追跡対象 / 非追跡対象
✅ 追う：AIサービスのセキュリティ・プライバシー設定変更、法人プラン変更、CVE・脆弱性、MCP/hooks等の実装トピック
❌ 追わない：単なる新モデルリリース速報、技術スペック解説、他社比較ランキング、一般市場動向

---

## 2. youtube-producer

### 役割
動画1本あたりの台本・タイトル・サムネ・説明文・チャプター・Shorts候補を統合生成。

### インプット
- テーマ（article-planner 経由 or でぐさん直指定）
- ターゲット読者
- 関連experiments / screenshots
- 備考

### アウトプット形式

```
===VIDEO_TITLE_OPTIONS===
タイトル案3つ（3〜4語の強キーワード、具体性、数字・結果入り）

===THUMBNAIL_TEXT_OPTIONS===
サムネ用テキスト案2〜3（各3〜4語、インパクト優先）

===THUMBNAIL_DIRECTION===
サムネのビジュアル方向性

===OPENING_30SEC_SCRIPT===
0-3秒: 結論先出し
3-8秒: なぜ重要か
8-30秒: 本編への導線

===MAIN_SCRIPT===
本編の流れ（何をどの順で見せる・話すか）

===DESCRIPTION===
説明文（最初の100文字重視、関連記事URL・LINE・資料室への導線）

===CHAPTERS===
タイムスタンプ付き見出し（5〜8個）

===TAGS===
5〜10個

===ENGAGEMENT_HOOKS===
中盤でのコメント誘発文言・チャンネル登録誘導のタイミング

===SHORTS_CLIP_CANDIDATES===
切り抜き3本の提案（各30〜45秒）
- 切り抜き1: タイトル/尺/フック/完結文
- 切り抜き2: 〃
- 切り抜き3: 〃
```

### 2026年YouTubeアルゴリズム対応
- **視聴維持率が最重要**、特に最初の30秒
- **CTR vs 冒頭離脱** が「Quality CTR」で判定される（クリックベイト逆効果）
- **満足度シグナル**（いいね・シェア・コメント）が急上昇中
- **Shorts は完走率が主要シグナル**、30〜45秒が黄金尺
- 冒頭30秒テンプレ：0-3秒 結論、3-8秒 なぜ重要、8-30秒 本編への導線
- 登録誘導は中盤1回のみ

---

## 3. article-writer

### 役割
記事下書きを**Markdown**で生成（SWELL HTML変換は publisher が担当）。

### インプット
- テーマ、ターゲット読者、キーワード
- experiments / screenshots
- youtube-producer の出力（連動する場合、台本と整合）

### アウトプット形式

```
===TITLE===
最終タイトル（1行、コロン禁止）

===SLUG===
英語スラッグ（小文字ハイフン）

===META===
meta description（120文字程度）

===BODY===
Markdown本文（CLAUDE.mdの記事構造に従う）

===TAGS===
タグ候補2〜4個（カンマ区切り）
```

### 記事構造
CLAUDE.md の「記事の構造」に従う（著者・最終更新日冒頭、この記事で分かること、各H2直下の要約、2026年SEO対応）。

### 2026年Google SEO対応
- E-E-A-T の Experience 重視（実体験・固有名詞・数字・スクショ）
- AI Overviews 引用対策（H2直下要約、表・リスト活用）
- 独自視点・空白地帯を狙う
- 冒頭で価値宣言
- 文字数目安 5,000〜6,000字

---

## 4. resource-maker

### 役割
**撮影時の進行台本＝配布資料**を Markdown で生成。ラボの棚（resource CPT）に掲載。

### インプット
- テーマ
- 関連記事（article-writer の出力）
- 関連動画台本（youtube-producer の出力）
- experiments / screenshots

### アウトプット形式

```
===TITLE===
===SLUG===
===META===
===BODY===
最終更新: 2026年X月Y日（版: v1.0）
対象: 中小企業の経営者・情シス担当
著者: 出口宣佳（コレットラボ）

## この資料でできること
（2〜3行）

## 手順 / 本文
（コードブロック、スクショ参照、操作手順）

## 次のアクション

## 更新履歴
- 2026年X月Y日 v1.0: 初版公開

## 免責事項
本資料の内容は2026年X月Y日時点の情報です。
実施は自己責任でお願いします。

### 📱 LINE公式で最新資料の更新通知を受け取る
→ {{LINE_URL}}

### 🏢 自社のAI導入を相談したい方
→ お問い合わせはこちら

© 2026 株式会社コレットラボ｜出口宣佳（でぐ）
```

### 保存先
`drafts/resources/YYYYMMDD_slug.md`

---

## 5. publisher

### 役割
Markdown → SWELL HTML変換 + 画像アップロード + WordPress下書き投稿。記事・資料両対応。

### インプット
- Markdownファイル（`drafts/*.md` or `drafts/resources/*.md`）
- 種別（article / resource）

### 処理フロー

1. **マーカー解析**: ===TITLE===, ===SLUG===, ===META===, ===BODY===, ===TAGS===
2. **Markdown → SWELL HTML 変換**:
   - 標準Markdown → HTML
   - `{{mark:...}}` → `<span class="swl-marker mark_yellow"><strong>...</strong></span>`
   - `{{point:...}}` → `<p class="is-style-big_icon_point">...</p>`
   - `{{caution:...}}` → `<p class="is-style-big_icon_caution">...</p>`
   - ```` ```bash ```` → `<div class="hcb_wrap"><pre class="prism line-numbers lang-bash">...</pre></div>`
   - 標準リスト → `<ul class="wp-block-list -list-under-dashed">...</ul>`
   - `### Q:` + `A:` → SWELL FAQブロック
3. **画像アップロード**:
   - Markdown内 `![](screenshots/xxx.png)` を検出
   - WordPress メディアにアップロード
   - 本文中のパスを WP URL に置換
4. **WordPress投稿**:
   - wp-auto-publish の `wp_publisher.py` を呼び出し
   - article → カスタム投稿タイプ `ai-lab`、下書き状態
   - resource → カスタム投稿タイプ `resource`、下書き状態、パスワード保護
5. **メタ設定**: SEO SIMPLE PACK のメタディスクリプション、SWELL のサムネ
6. **完了後**: drafts/ → published/ へ移動、投稿URLを返す

### 資料に付随する実用素材（Word/Excel/ZIP）の扱い
- `experiments/` 等にあるファイルを WP メディアにアップロード
- 資料ページ内にダウンロードリンクを埋め込む
- PDF の自動生成は**行わない**

### 公開ボタンは**絶対に自動化しない**
下書き投稿までが自動。公開は管理画面から人間が最終確認して実行。

---

## 6. sns-composer

### 役割
記事・動画の内容をベースに、**X / Threads / Instagram** 用の投稿文案を自動生成。

### インプット
- 記事（article-writer の出力）
- 動画（youtube-producer の台本・Shorts候補）
- 切り抜き指定（任意）

### アウトプット

**X（140字・毎日3〜5本向け）**
```
投稿案1: 結論一発型
投稿案2: 引用型（尖った1文）
投稿案3: 問いかけ型
投稿案4: ビフォーアフター型
投稿案5: 失敗談型
```

**Threads（500字・毎日1本以上）**
```
投稿案1: 中尺展開版
投稿案2: 記事要約独自ポスト
返信候補: 他アカへのコメント候補3本
```

**Instagram（Reelsキャプション）**
```
Reelsキャプション案（ハッシュタグ含む）
```

### アルゴリズム対応（2026年）

**X:**
- Reply誘発で終わる（×13.5〜27の重み）、会話往復が最強（×150）
- URL は本文に貼らず最初のリプライへ（外部リンク抑制対策）
- 画像・動画必須（テキストのみはハンデ）
- 1ツイート完結
- Bookmark誘発（チェックリスト、Tips）
- 時間減衰急：投稿後30分が勝負

**Threads:**
- エンゲージメント速度重視（30分以内のリアクション）
- 画像付き基本
- 問いかけで終わる（リプライ誘発）
- URL貼ってOK（X と違う）
- 独自観察・本音
- 投稿＋返信候補セットで生成（Mosseri曰く返信=投稿と同等価値）

**Instagram（Reels）:**
- **3秒フック**を冒頭に（Watch Time 3秒維持が最低ライン）
- 短めReels推奨（15〜30秒、完走率重視）
- Share Rate を高める内容（「DMで送りたい」と思わせる）
- オリジナル必須（30日で10本以上リポストで推薦除外）
- ハッシュタグは補助（Watch Time が主）

### 活用画像案
投稿案ごとに「この画像（スクショまたはアイキャッチ）と組み合わせると良い」を添える。

### 文体
CLAUDE.md の文体ルール・尖り vs 煽りに従う。煽り系（「〜しないと事故る」）は禁止。
