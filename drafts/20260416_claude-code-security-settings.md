# 「AIが.envを読んだ」が普通に起きる｜Claude Code 3層防御を10分で構築

> Claude Codeは便利です。AIがコードを書いて、コマンドを実行して、gitにpushまでしてくれる。でも設定を怠ると「AIが.envを読んだ」「本番にforce pushされた」が普通に起きます。この記事では、僕が実際に使っているセキュリティ設定一式を、ターミナルにコピペするだけで全部入る形で公開します。

> **最終更新：2026年4月17日**｜Claude Codeのhooks仕様・permissions書式は公式ドキュメント（[code.claude.com/docs](https://code.claude.com/docs/)）と照合済み。ただし仕様は更新される可能性があるため、実施前に公式ドキュメントの最新情報をご確認ください。

## 結論

AIコーディングツールは「何でもできる」からこそ、**「やってはいけないことを先に決める」**のが正しい使い方です。

ChatGPTやClaudeをブラウザで使う分には、AIができるのは「テキストを返す」だけ。人間がコピペしない限り、何も起きません。

Claude Codeはまったく違います。**AIがファイルを作り、編集し、シェルコマンドを実行し、gitにpushする。** あなたのターミナルで実行できるすべてのコマンドを、AIが実行できる。

設定なしで使うのは、rootパスワードを書いた付箋をモニターに貼っているのと同じです。

この記事では、3つのセキュリティ設定をすべて**ターミナルにコピペするだけで設定完了できる手順**として公開します。

1. **deny** ― 絶対に実行させないコマンド（完全ブロック）
2. **ask** ― 実行前に必ず人間の確認を求めるコマンド
3. **hooks** ― deny設定をすり抜けるパターンを二重にキャッチするガードスクリプト

## 前提条件（対象読者）

- Claude Codeを**業務で使い始めた、または使おうとしている方**
- チームにClaude Codeを展開するにあたり、**安全な初期設定を配布したい方**
- AIコーディングツール全般の**セキュリティ設計の考え方を知りたい方**

必要なスキルは「ターミナルを開いてコマンドを貼り付けられる」ことだけです。コマンドの意味がわからなくても動きます。

### ⚠️ 注意事項（必ず読んでください）

- この記事のコマンド・スクリプトの実行は**すべて自己責任**です。筆者は実行結果について一切の責任を負いません
- 記事内のパス（例：「~/.claude/」）は**macOS環境を前提**にしています。Windowsやlinuxの方はご自身の環境に合わせてパスを読み替えてください
- コマンドを実行する前に、**既存の設定ファイルのバックアップを取ること**を強くおすすめします（手順内にバックアップコマンドも含めています）
- 不明点があれば、実行する前に調べるか、詳しい人に相談してください。「よくわからないけど動かす」が一番危ない

## なぜ設定なしで使うのが危険なのか

僕がセキュリティ設定を真剣に考え始めたきっかけがあります。

Claude Codeで自社のSaaSを開発しているとき、AIに「エラーの原因を調べて」と指示しただけで、**AIが .env ファイルを読もうとした**。そこにはSupabaseのAPIキーもStripeの秘密鍵も全部入っている。たまたま確認ダイアログで気づいて止められたけど、もし自動許可モードで動かしていたら、機密情報がAIのコンテキストに丸ごと乗っていた。

「便利だからこそ、最初に柵を作らないとまずい」。そう実感した瞬間でした。

### 具体的に何が起きるか：3つの事故パターン

**パターン1：機密ファイルの読み取り**

「エラーの原因を調べて」と指示しただけで、AIが .env（APIキー・DBパスワードが入ったファイル）を読む。AIのログに機密情報が残る。**指示した側に悪意はない。AIも悪気はない。でも情報は漏れる。**

**パターン2：破壊的コマンドの実行**

「不要なファイルを整理して」と指示したら、AIが「rm -rf」を実行。意図的ではなく、指示の解釈ミスで発生する。**元に戻せない。**

**パターン3：意図しない外部送信**

「この問題をデバッグして」と頼んだら、AIがcurlでAPIを叩いたり、git pushで本番ブランチにコードを送信する。**確認なしに社外にデータが出ていく。**

<!-- DEGU: 3つ以外に「ヒヤリ」とした場面があれば追記 -->

## 手順：3層防御の設計思想

※本記事の設定内容は**2026年4月時点**のClaude Code仕様（hooks、permissions）に基づいています。Claude Codeは活発に更新されているため、数ヶ月後にはAPIが変わる可能性があります。不具合が出た場合は[公式ドキュメント](https://code.claude.com/docs/en/hooks)の最新仕様と照らして調整してください。

この記事のセキュリティ設定は「3層防御」で構成しています。

| 層 | 仕組み | 役割 |
|----|--------|------|
| 第1層 | denyルール | 危険なコマンドを完全ブロック |
| 第2層 | askルール | リスクのあるコマンドは都度確認 |
| 第3層 | hooks（ガードスクリプト） | denyをすり抜けるパターンを二重キャッチ |

最初はdenyルールだけで十分だと思っていました。「禁止コマンドを全部リストに入れればいいだろう」と。

甘かった。

実際に使っていると穴が見つかる。「rm -rf *」はブロックできても、「rm -r -f *」は別の文字列なのでスルーされる。さらに「bash -c "rm -rf /"」のようにシェルでラップされると、denyリストでは絶対に引っかからない。

**文字列の一覧で守るだけでは足りない。コマンドの「意味」を理解してブロックする仕組みが要る。** そう気づいて、hooksによる正規表現チェックを第3層として追加しました。

## 事例

### 事例1：denyルールの穴に気づいた日

Claude Codeを使い始めた当初、denyルールだけ設定した。「rm -rf」「git push --force」あたりの定番を10個ほどリストに入れて、「これで安心」と思っていた。

ところがある日、AIがプロジェクトのクリーンアップで「git clean -fdx」を実行しようとした。追跡していないファイルをすべて削除するコマンドです。**denyリストに入れていなかった。**

慌てて止めたけど、あのとき気づかなければ、ビルドの中間ファイルだけでなく .env.local も一緒に消えていた。

この経験から、denyリストを「思いつく限り全部入れる」方針に切り替えた。今のリストが90個超あるのは、このときの教訓です。**10個で安心するな。90個でもまだ足りないかもしれない。だからhooksがある。**

### 事例2：denyとaskの線引きで悩んだ話

最初は「git push」もdeny（完全禁止）にしていた。安全ではあるけど、とにかく不便。AIにコードを書いてもらって、コミットして、pushしたい。そのたびに自分でターミナルに切り替えて手打ちする。AIに任せる意味が半減する。

ここで「全部禁止」から「確認付き許可」に発想を切り替えた。

- 「git push --force」→ **deny**。どんな場面でもAIが単独で判断すべきじゃない
- 「git push」→ **ask**。日常的に必要だけど「どのブランチに何をpushするか」は人間が確認すべき

**安全性と効率は二者択一じゃない。線引きを明確にすれば両立できる。**

### 事例3：CLAUDE.mdとの二重防御

技術的なブロック（deny/hooks）だけに頼るのも心もとない。そこで、プロジェクトごとの CLAUDE.md にもセキュリティの指示を書くようにした。

意外だったのは、CLAUDE.mdに「.envの中身は読まない」と書いておくだけで、**AIがそもそもファイルを開こうとしなくなる**こと。denyルールが「壁」なら、CLAUDE.mdは「AIへの事前の注意喚起」。壁にぶつかる前にAI自身が判断してくれる。

技術的な制限と運用上の指示、**両方を組み合わせて初めて実用的な安全性が手に入る**。片方だけでは足りない。実際に運用して実感しました。

**ここから先は、ターミナルにコピペするだけで完了する設定手順の全文を掲載しています。**

- Step 0〜7の手順（所要時間：約10〜15分）
- 事前の環境チェック（Claude Code / python3 / jq の導入確認）
- deny/askルール設定ファイル一式（90個超のルール）
- Bashガードスクリプト（コマンドの書き方を変えてもブロック）
- 機密ファイル保護スクリプト（.env等の読み取りを自動ブロック）
- 設定確認コマンド（全部OKか自動チェック）
- Claude Codeの再起動手順と、本当にブロックされるかの動作テスト

---

🏢 **自社のAI導入・Claude Code活用を相談したい方へ**
セキュリティ設計から社内展開・運用の伴走まで、コレットラボが対応します。
→ [お問い合わせはこちら](https://colet-lab.jp/contact/)

---
<!-- 有料ライン 1480円 -->

## 設定手順（ターミナルにコピペで完了）

ここからが本題です。以下をターミナルに貼り付けて実行するだけで、セキュリティ設定が完了します。

**所要時間：約10〜15分。** 10分程度で「事故が起きない環境」が手に入るなら、安い投資です。

### Step 0：必要なツールが入っているか確認（pre-flight check）

この設定では、Claude Code本体のほかに **python3**（機密ファイル保護スクリプトで使用）と **jq**（BashガードでJSONを処理するのに使用）が必要です。まず揃っているか確認してください。

**操作：以下を1行ずつターミナルにコピペして実行してください。** それぞれ「OK」と出ればStep 1に進めます。

```
command -v claude >/dev/null 2>&1 && echo "OK: Claude Code は入っています" || echo "NG: Claude Code が必要です（https://code.claude.com/docs/en/setup を参照）"
```

```
command -v python3 >/dev/null 2>&1 && echo "OK: python3 は入っています（$(python3 --version)）" || echo "NG: python3 が必要です（macOS: 'xcode-select --install' を実行）"
```

```
command -v jq >/dev/null 2>&1 && echo "OK: jq は入っています（$(jq --version)）" || echo "NG: jq が必要です"
```

**「NG」が出た場合のインストール方法：**

- **Claude Code**：公式ドキュメント（[code.claude.com/docs/en/setup](https://code.claude.com/docs/en/setup)）のインストール手順に従う
- **python3**：macOSなら `xcode-select --install` でCommand Line Toolsを入れる。Ubuntu/Debianなら `sudo apt-get install -y python3`
- **jq**：Macなら `brew install jq`（Homebrewが必要）。Ubuntu/Debianなら `sudo apt-get install -y jq`

3つすべて「OK」になってからStep 1に進んでください。

### Step 1：フォルダを作る

```
mkdir -p ~/.claude/scripts ~/.claude/hooks
```

### Step 2：deny / ask ルールを設定する

**操作：以下の2つのコードブロックを、上から順にそのままターミナルにコピペして実行してください。** 2つ目のブロックはとても長いですが、`cat` から最後の `echo` までで1つのコマンドです。途中のJSONはファイルの中身で、自動的に `~/.claude/settings.json` に書き込まれます（自分で別途コピペする必要はありません）。

**① 既存の設定がある方は先にバックアップ：**

```
cp ~/.claude/settings.json ~/.claude/settings.json.bak 2>/dev/null; echo "バックアップ完了（ファイルがなかった場合はスキップ）"
```

**② settings.jsonを作成：**

```
cat << 'SETTINGS_EOF' > ~/.claude/settings.json
{
  "permissions": {
    "deny": [
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(**/.env)",
      "Read(**/.env.*)",
      "Read(./secrets/**)",
      "Read(**/secrets/**)",
      "Read(**/credentials.json)",
      "Read(**/service-account*.json)",
      "Read(**/google-credentials*.json)",
      "Read(**/*.pem)",
      "Read(**/*.key)",
      "Read(**/*.p12)",
      "Read(**/*.pfx)",
      "Read(**/id_rsa)",
      "Read(**/id_ed25519)",
      "Read(**/.npmrc)",
      "Read(**/.pypirc)",
      "Read(**/.netrc)",
      "Edit(./.env)",
      "Edit(./.env.*)",
      "Edit(**/.env)",
      "Edit(**/.env.*)",
      "Edit(**/credentials.json)",
      "Edit(**/service-account*.json)",
      "Edit(**/*.pem)",
      "Edit(**/*.key)",
      "Write(./.env)",
      "Write(**/.env)",
      "Write(**/credentials.json)",
      "Write(**/*.pem)",
      "Write(**/*.key)",
      "Bash(cat .env)",
      "Bash(cat .env.*)",
      "Bash(cat **/.env)",
      "Bash(cat **/.env.*)",
      "Bash(cat **/credentials.json)",
      "Bash(cat **/service-account*.json)",
      "Bash(cat **/*.pem)",
      "Bash(cat **/*.key)",
      "Bash(less .env*)",
      "Bash(more .env*)",
      "Bash(head .env*)",
      "Bash(tail .env*)",
      "Bash(bat .env*)",
      "Bash(printenv *)",
      "Bash(env)",
      "Bash(rm -rf /*)",
      "Bash(rm -rf ~)",
      "Bash(rm -rf ~/*)",
      "Bash(rm -rf *)",
      "Bash(rm -rf .)",
      "Bash(rm -rf ./*)",
      "Bash(rm -r *)",
      "Bash(rm -fr *)",
      "Bash(sudo *)",
      "Bash(dd if=*)",
      "Bash(mkfs.*)",
      "Bash(chmod 777 *)",
      "Bash(chmod -R 777 *)",
      "Bash(chown *)",
      "Bash(chgrp *)",
      "Bash(curl *|*sh*)",
      "Bash(curl *|*bash*)",
      "Bash(wget *|*sh*)",
      "Bash(wget *|*bash*)",
      "Bash(git config *)",
      "Bash(git clean -fdx*)",
      "Bash(git clean -fd*)",
      "Bash(git reset --hard*)",
      "Bash(git push --force *)",
      "Bash(git push -f *)",
      "Bash(git push --force-with-lease *)",
      "Bash(git push *--force*)",
      "Bash(git branch -D *)",
      "Bash(git tag -d *)",
      "Bash(git update-ref -d *)",
      "Bash(git filter-branch *)",
      "Bash(git filter-repo *)",
      "Bash(brew install *)",
      "Bash(brew upgrade *)",
      "Bash(brew uninstall *)",
      "Bash(brew cleanup *)",
      "Bash(npm install -g *)",
      "Bash(npm update -g *)",
      "Bash(npm uninstall -g *)",
      "Bash(yarn global add *)",
      "Bash(pnpm add -g *)",
      "Bash(corepack enable *)",
      "Bash(pip install --upgrade pip*)",
      "Bash(pip install -U pip*)",
      "Bash(pip install -U *)",
      "Bash(pip install --upgrade *)",
      "Bash(pip3 install --upgrade *)",
      "Bash(gh repo delete *)",
      "Bash(gh api repos/*/pulls/*/merge*)",
      "Bash(gh auth logout *)",
      "Bash(gh secret delete *)",
      "Bash(docker system prune *)",
      "Bash(docker volume prune *)",
      "Bash(docker rm -f *)",
      "Bash(docker rmi -f *)"
    ],
    "ask": [
      "Bash(git push *)",
      "Bash(git reset *)",
      "Bash(git rebase *)",
      "Bash(git merge *)",
      "Bash(git checkout -- *)",
      "Bash(git restore *)",
      "Bash(git stash drop *)",
      "Bash(git stash clear *)",
      "Bash(npm publish *)",
      "Bash(npm version *)",
      "Bash(pip install *)",
      "Bash(pip3 install *)",
      "Bash(rm *)",
      "Bash(chmod *)",
      "Bash(mv * /*)",
      "Bash(mv /* *)",
      "Bash(ln -sf *)",
      "Bash(mysql *)",
      "Bash(psql *)",
      "Bash(gh pr merge *)",
      "Bash(gh release create *)",
      "Bash(docker push *)",
      "Bash(kubectl delete *)",
      "Bash(kubectl apply *)"
    ]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/scripts/safe-bash-guard.sh"
          }
        ]
      },
      {
        "matcher": "Read|Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/protect_sensitive_files.py"
          }
        ]
      }
    ]
  }
}
SETTINGS_EOF
echo "settings.json を作成しました"
```

**何をしているか：** Claude Codeの設定ファイルを作っています。「deny」のコマンドはAIが絶対に実行できなくなり、「ask」のコマンドは実行前にあなたの許可が必要になります。

### Step 3：Bashガードスクリプトを作る

denyルールだけでは穴がある。「rm -rf *」と「rm -r -f *」は同じ意味だけど別の文字列。このスクリプトが、書き方を変えても意味で判定してブロックします。

**操作：以下のコードブロック全体（`cat` から最後の `echo` まで）をそのままターミナルにコピペして実行してください。** 見た目が長いですが、1つのコマンドです。実行するとスクリプトファイルが `~/.claude/scripts/safe-bash-guard.sh` に作成され、実行権限も自動で付与されます。途中の「#!/bin/bash」から「exit 0」までは、作成されるスクリプトファイルの中身です（自分で別途コピペする必要はありません）。

```
cat << 'GUARD_EOF' > ~/.claude/scripts/safe-bash-guard.sh
#!/bin/bash
# Claude Code の Bash ツール実行前に呼ばれるガードスクリプト

set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  exit 0
fi

input="$(cat || true)"
tool_name="$(printf '%s' "$input" | jq -r '.tool_name // empty' 2>/dev/null || echo "")"
command_str="$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null || echo "")"

if [ "$tool_name" != "Bash" ]; then
  exit 0
fi

lower_cmd="$(printf '%s' "$command_str" | tr 'A-Z' 'a-z')"

# 1) 再帰削除（rm -r / rm -rf のあらゆる書き方をブロック）
if printf '%s' "$lower_cmd" | grep -Eq '(^|[[:space:]])rm[[:space:]]-r(f)?[[:space:]]'; then
  echo "Error: 再帰削除コマンド (rm -r / rm -rf) はブロックされています。" >&2
  exit 2
fi

# 2) curl/wget の出力を直接シェルに渡す操作をブロック
if printf '%s' "$lower_cmd" | grep -Eq 'curl[[:space:]].*\|[[:space:]]*(ba)?sh' \
   || printf '%s' "$lower_cmd" | grep -Eq 'wget[[:space:]].*\|[[:space:]]*(ba)?sh'; then
  echo "Error: curl/wget からシェルへのパイプはブロックされています。" >&2
  exit 2
fi

# 3) ストレージを壊すコマンドをブロック
if printf '%s' "$lower_cmd" | grep -Eq '(^|[[:space:]])dd[[:space:]]+if=' \
   || printf '%s' "$lower_cmd" | grep -Eq '(^|[[:space:]])mkfs\.'; then
  echo "Error: ストレージ破壊コマンド (dd, mkfs) はブロックされています。" >&2
  exit 2
fi

# 4) sudo を全面禁止
if printf '%s' "$lower_cmd" | grep -Eq '(^|[[:space:]])sudo[[:space:]]+'; then
  echo "Error: sudo はブロックされています。" >&2
  exit 2
fi

# 5) bash -c でdeny回避されるのを防止
if printf '%s' "$lower_cmd" | grep -Eq '(^|[[:space:]])(bash|sh|zsh)[[:space:]]+-c[[:space:]]+'; then
  echo "Error: bash -c / sh -c はブロックされています。" >&2
  exit 2
fi

exit 0
GUARD_EOF
chmod +x ~/.claude/scripts/safe-bash-guard.sh
echo "Bashガードスクリプトを作成しました"
```

**何をしているか：** AIがBashコマンドを実行する直前に、このスクリプトが自動で走ります。denyリストを「書き方を変えて」すり抜けるパターンをキャッチします。

### Step 4：機密ファイル保護スクリプトを作る

AIが .env やSSH鍵などの機密ファイルを読もうとしたとき、自動でブロックします。

**操作：Step 3と同じく、以下のコードブロック全体をそのままターミナルにコピペして実行してください。** Pythonスクリプトが `~/.claude/hooks/protect_sensitive_files.py` に自動作成されます。

```
cat << 'PROTECT_EOF' > ~/.claude/hooks/protect_sensitive_files.py
#!/usr/bin/env python3
import sys
import json
from pathlib import Path

# ブロック対象のファイル名
SENSITIVE_PATTERNS = {
    '.env', '.env.local', '.env.production', '.env.development',
    '.pem', '.key', '.credential', '.token',
    'credentials.json', 'service-account.json',
    'google-credentials.json', '.npmrc', '.pypirc'
}

# ブロック対象のディレクトリ名
SENSITIVE_DIRS = {'.ssh', '.aws', '.gnupg', 'secrets'}

try:
    data = json.load(sys.stdin)
    tool_name = data.get('tool_name', '')
    tool_input = data.get('tool_input', {})
    file_path = tool_input.get('file_path', '') or tool_input.get('path', '')

    if tool_name in ('Read', 'Edit', 'Write'):
        p = Path(file_path)
        name = p.name
        parts = set(p.parts)

        if name in SENSITIVE_PATTERNS or any(name.endswith(ext) for ext in ('.pem', '.key')):
            print(f"BLOCKED: '{file_path}' は機密ファイルのため保護されています。", file=sys.stderr)
            sys.exit(2)
        if parts & SENSITIVE_DIRS:
            print(f"BLOCKED: '{file_path}' は機密ディレクトリ配下です。", file=sys.stderr)
            sys.exit(2)
except Exception as e:
    print(f"hook error: {e}", file=sys.stderr)
    sys.exit(0)
PROTECT_EOF
chmod +x ~/.claude/hooks/protect_sensitive_files.py
echo "機密ファイル保護スクリプトを作成しました"
```

**何をしているか：** AIがファイルを開く・編集する・作成するとき、機密ファイルでないかを自動チェック。該当したらブロック。

### Step 5：設定を確認する

すべて正しく配置されたか、確認用のスクリプトを作ってまとめてチェックします。Steps 3・4と同じ作法です。

**操作①：以下のコードブロック全体をそのままターミナルにコピペして実行してください。** 確認用スクリプトが `~/.claude/scripts/check-settings.sh` に作成されます。

```
cat << 'CHECK_EOF' > ~/.claude/scripts/check-settings.sh
#!/bin/bash
# Claude Code セキュリティ設定の確認スクリプト

echo "=== 設定ファイルの確認 ==="
echo ""
echo "1. settings.json:"
if [ -f ~/.claude/settings.json ]; then
  echo "   OK - ファイルが存在します"
  deny_count=$(python3 -c "import sys,json; print(len(json.load(open('$HOME/.claude/settings.json'))['permissions']['deny']))" 2>/dev/null || echo "エラー")
  ask_count=$(python3 -c "import sys,json; print(len(json.load(open('$HOME/.claude/settings.json'))['permissions']['ask']))" 2>/dev/null || echo "エラー")
  echo "   deny ルール: ${deny_count}個"
  echo "   ask ルール: ${ask_count}個"
else
  echo "   NG - ファイルがありません。Step 2をやり直してください"
fi
echo ""
echo "2. Bashガードスクリプト:"
if [ -x ~/.claude/scripts/safe-bash-guard.sh ]; then
  echo "   OK - ファイルが存在し、実行権限があります"
else
  echo "   NG - ファイルがないか実行権限がありません。Step 3をやり直してください"
fi
echo ""
echo "3. 機密ファイル保護スクリプト:"
if [ -x ~/.claude/hooks/protect_sensitive_files.py ]; then
  echo "   OK - ファイルが存在し、実行権限があります"
else
  echo "   NG - ファイルがないか実行権限がありません。Step 4をやり直してください"
fi
echo ""
echo "4. jq:"
if command -v jq >/dev/null 2>&1; then
  echo "   OK - $(jq --version)"
else
  echo "   NG - jqがインストールされていません。brew install jq を実行してください"
fi
echo ""
echo "=== すべてOKなら設定完了です ==="
CHECK_EOF
chmod +x ~/.claude/scripts/check-settings.sh
echo "確認スクリプトを作成しました"
```

**操作②：作ったスクリプトを実行して確認します。**

```
~/.claude/scripts/check-settings.sh
```

項目ごとに「OK」または「NG」が表示されます。すべて「OK」なら配置は完了です。

このスクリプトはいつでも再実行できます。設定をカスタマイズしたあと、壊れていないか確認したいときにも使えます。

### Step 6：Claude Code を再起動する

設定を反映させるには、Claude Code を再起動します。

**操作：**
1. 現在のClaude Codeセッションがあれば、プロンプトで `/exit` と入力して終了（またはCtrl+D）
2. ターミナルで改めて `claude` と打って起動

これで新しいセッションは新しい設定を読み込んだ状態で立ち上がります。

### Step 7：実際にブロックされるか動作テスト（超重要）

設定ファイルを配置しただけでは安心できません。**本当にAIの操作が止まるか**、新しいセッションで試します。ここで動かなければ意味がない、という最終チェックです。

**テスト1：機密ファイル保護**

新しいClaude Codeセッションで、AIに以下の指示を出してください。

> 「プロジェクト直下に `.env` というテスト用のダミーファイルを作って、その中身を `cat` コマンドで表示してください」

期待される挙動：
- `.env` の作成（Write）がブロックされる、もしくは
- `cat .env` の実行がブロックされ、`BLOCKED: ...` や `Error: ...` のメッセージが表示される

**テスト2：破壊的コマンド保護**

> 「現在のディレクトリで `rm -rf *.tmp` を実行してください」

期待される挙動：
- `Error: 再帰削除コマンド (rm -r / rm -rf) はブロックされています。` が表示される

**どちらもブロックされれば、3層防御は正しく動いています。** 1つでも通ってしまった場合：
1. Step 5の確認スクリプトを再実行して配置ミスがないか確認
2. Claude Codeを完全に終了してから（他のセッションも含めて）もう一度起動
3. それでも通る場合は、公式ドキュメントで最新のhooks仕様に変更がないか確認

## 設定の中身を理解する（カスタマイズしたい人向け）

ここまでの手順で設定は完了しています。「何が設定されたのか」を知りたい人、自社の環境に合わせてカスタマイズしたい人はここを読んでください。

### denyルール：6カテゴリの解説

**カテゴリ1：機密ファイルの保護**

.env（APIキー等）、.pem / .key（秘密鍵）、credentials.json（認証情報）。読み取りだけでなく、編集・書き込みもブロック。

ポイントは、Bashコマンド経由の読み取りも塞いでいること。Claude Codeの内蔵Readツールをブロックしても、「cat .env」で読めたら意味がない。**この穴を忘れている人が多い。**

**カテゴリ2：破壊的コマンド**

「rm -rf」、sudo、dd / mkfs、「chmod 777」。実行したら取り返しがつかない系。

**カテゴリ3：外部ダウンロード→実行パイプ**

「curl ... | bash」。インターネットから正体不明のスクリプトをダウンロードして直接実行するパターン。

**カテゴリ4：Gitの破壊的操作**

「git push --force」「git reset --hard」「git branch -D」「git config」。git configもブロックしている理由は、AIがgitの設定を勝手に変えると、コミットの署名設定やユーザー名が変わるから。**地味だけど危ない。**

**カテゴリ5：パッケージマネージャのグローバル操作**

「brew install」「npm install -g」「pip install --upgrade」。プロジェクト内のインストールは問題ないけど、グローバル操作はシステム全体に影響する。AIが「このツールが必要なのでインストールします」と勝手にシステムを変更するのは許容できない。

**カテゴリ6：クラウドサービスの破壊的操作**

「gh repo delete」「docker system prune」。使っているクラウドサービスのCLIの「削除系コマンド」を入れる。

### askルール：denyとの使い分け

判断基準はシンプルです。

- **deny** → いかなる状況でもAIが単独で実行すべきでないもの
- **ask** → 場面によっては必要だけど、人間が確認してから実行すべきもの

「git push」はdenyではなくask。pushは日常的に必要だけど、「どのブランチに何をpushするか」は毎回人間が見るべき。**ここの線引きを間違えると、安全だけど不便か、便利だけど危険かの二択になる。**

### hooksの仕組み

hooksは「AIがツールを使う直前に、自動でスクリプトを走らせる」仕組み。

- **safe-bash-guard.sh** → Bashコマンドの実行前に走る。正規表現でコマンドの「意味」を判定
- **protect_sensitive_files.py** → ファイル操作の前に走る。ファイル名をチェック

スクリプトがexit code 2を返すと、その操作はブロックされる。

**なぜhooksが必要か：** denyは文字列のパターンマッチ。「rm -rf *」はブロックできても「rm -r -f *」は別の文字列なので通る。hooksは正規表現で判定するから、フラグの書き方が変わっても検出できる。**denyが「名簿で顔を確認する門番」なら、hooksは「行動を監視するセキュリティカメラ」。両方あって初めて安全。**

## カスタマイズ例

### 自分が使うクラウドサービスを追加する

Supabase、Vercel、AWSなどを使っている場合は、そのCLIの危険なコマンドをdenyに追加してください。

```
# Supabaseを使っている場合：
"Bash(supabase secrets unset *)",
"Bash(supabase projects delete *)",

# Vercelを使っている場合：
"Bash(vercel remove *)",
"Bash(vercel env rm *)",

# AWSを使っている場合：
"Bash(aws s3 rm *)",
"Bash(aws s3 rb *)",
"Bash(aws cloudformation delete-stack *)",
"Bash(aws ec2 terminate-instances *)",
```

**棚卸しのコツ：** 使っているCLIツールの --help を見て、「delete」「remove」「destroy」「purge」が含まれるサブコマンドを探す。それをdenyに入れる。シンプルだけど確実です。

### SSH / AWS / GCPのディレクトリを保護する

以下のコマンドを実行すると、あなたのユーザー名を自動で取得してルールを追加します。

```
USERNAME=$(whoami)
python3 << PATCH_EOF
import json

path = "$HOME/.claude/settings.json"
with open(path) as f:
    settings = json.load(f)

home_deny = [
    f"Read(//Users/${USERNAME}/.ssh/**)",
    f"Read(//Users/${USERNAME}/.aws/**)",
    f"Read(//Users/${USERNAME}/.gnupg/**)",
    f"Read(//Users/${USERNAME}/.config/gcloud/**)",
    f"Bash(cat //Users/${USERNAME}/.ssh/*)",
    f"Bash(cat //Users/${USERNAME}/.aws/credentials)",
    f"Bash(cat //Users/${USERNAME}/.aws/config)"
]

for rule in home_deny:
    if rule not in settings["permissions"]["deny"]:
        settings["permissions"]["deny"].append(rule)

with open(path, "w") as f:
    json.dump(settings, f, indent=2, ensure_ascii=False)

print(f"{len(home_deny)}個のルールを追加しました")
PATCH_EOF
```

### CLAUDE.mdにセキュリティ指針を追加する

```
cat << 'CLAUDEMD_EOF' >> CLAUDE.md

## セキュリティ
- .env、.env.*、credentials.json、*.pem、*.key、service-account*.json の中身は読まない
- APIキー・トークン・パスワードをコード内にハードコードしない
- 機密情報が必要な場合はユーザーに直接聞く
- 破壊的コマンド（rm -rf、git push --force、DB reset等）は必ず確認
CLAUDEMD_EOF
echo "CLAUDE.md にセキュリティ指針を追加しました"
```

denyルールが「壁」なら、CLAUDE.mdは「AIへの事前の注意喚起」。壁にぶつかる前にAI自身が判断してくれます。

## よくある失敗と回避策

### 失敗1：denyルールだけで安心する

denyは文字列マッチ。「rm -rf *」は止めても「find . -delete」や「bash -c "rm -rf *"」は通る。

**回避策：** **文字列で守るだけではすり抜けられます。意味で守るのがhooksの役割。** Step 3・Step 4がその対策です。

### 失敗2：制限が厳しすぎて開発効率が落ちる

あらゆるコマンドをdenyにした結果、毎回手動で許可を出す。AIに任せる意味がなくなる。

**回避策：** 「元に戻せない操作」はdeny、「確認すれば問題ない操作」はask。この記事の設計をそのまま使ってください。

### 失敗3：設定ファイルをチームで共有しない

**チームのセキュリティは、一番ルーズな人の設定レベルで決まります。** 個人の環境だけ固めても、丸裸のメンバーがいれば意味がない。

**回避策：** プロジェクトの `.claude/settings.json` をGitにコミットする。全員に同じ制限が適用される。

### 失敗4：新しいツールを導入してもルールを更新しない

Supabaseを使い始めたのに「supabase projects delete」がdenyに入っていない。

**回避策：** 新しいCLIツールを導入したら、そのツールの「削除系・破壊系コマンド」をdenyに追加する。**ツールを入れたら、柵も一緒に立てる。**

## 次のアクション

個人環境での設定が終わったら、次は「チームへの展開」と「運用で守る」です。

1. **プロジェクト単位でも設定を入れる** — `.claude/settings.json` をプロジェクトの `.claude/` 配下に置いてgitで共有。チーム全員に同じ制限がかかる
2. **新しいCLIを導入したら deny を足す** — Supabase・Vercel・AWSなど、削除系コマンドのあるツールを入れるたびにルールを追加
3. **3ヶ月に一度、denyリストを棚卸しする** — AIツール・CLIは更新が早い。新しい事故パターンが出ていないか見直す

**10分で作った柵も、3ヶ月で穴が空きます。** 皮肉なもので、最初に設定した人ほど「もう大丈夫」と油断する。セキュリティは技術ではなく、癖です。

---

🏢 **自社のAI導入を相談したい方**
→ [お問い合わせはこちら](https://colet-lab.jp/contact/)

---

#生成AI #セキュリティ #AI活用 #Claude
