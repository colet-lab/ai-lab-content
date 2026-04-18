#!/bin/bash
#
# update_resource_password.sh — ラボの棚（resource CPT + 固定ページ）のパスワードを一括更新
#
# 使い方:
#   bash scripts/update_resource_password.sh <新しいパスワード>
#
# 前提:
#   - WP-CLI がサーバーで実行可能
#   - SSH でサーバーにアクセス可能、または WordPress 管理環境で直接 wp コマンドが使える
#   - 固定ページ「ラボの棚」のスラッグが "resources"
#   - カスタム投稿タイプが "resource"
#
# 例:
#   bash scripts/update_resource_password.sh colet-lab-2605

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "使い方: $0 <新しいパスワード>" >&2
  exit 1
fi

NEW_PASSWORD="$1"

# WP-CLI が利用可能か確認
if ! command -v wp >/dev/null 2>&1; then
  echo "❌ WP-CLI が見つかりません。" >&2
  echo "   サーバー上で実行するか、以下のURLで手動更新してください：" >&2
  echo "   https://colet-lab.jp/wp-admin/edit.php?post_type=resource" >&2
  echo "   https://colet-lab.jp/wp-admin/edit.php?post_type=page" >&2
  exit 1
fi

echo "🔑 月次パスワード更新: $NEW_PASSWORD"
echo ""

# 固定ページ「ラボの棚」更新
echo "📄 固定ページ「ラボの棚」を更新..."
LABO_ID=$(wp post list --post_type=page --name=resources --field=ID 2>/dev/null || echo "")
if [ -n "$LABO_ID" ]; then
  wp post update "$LABO_ID" --post_password="$NEW_PASSWORD" 2>&1 | tail -1
  echo "   ✅ ラボの棚（ID=$LABO_ID）更新完了"
else
  echo "   ⚠️ 固定ページ「ラボの棚」(slug=resources) が見つかりません"
fi
echo ""

# resource CPT 全更新
echo "📚 resource CPT を一括更新..."
COUNT=0
for id in $(wp post list --post_type=resource --field=ID 2>/dev/null); do
  wp post update "$id" --post_password="$NEW_PASSWORD" >/dev/null 2>&1
  COUNT=$((COUNT + 1))
done
echo "   ✅ $COUNT 件の資料を更新完了"
echo ""

echo "🎉 パスワード更新完了"
echo ""
echo "次のステップ:"
echo "  LINE公式で配信するパスワード: $NEW_PASSWORD"
echo "  月初のパスワード配信テンプレは docs/line-setup.md 参照"
