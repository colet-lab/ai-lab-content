#!/usr/bin/env python3
"""
publish.py — Markdown記事を WordPress (colet-lab.jp) に下書き投稿

使い方:
    python3 scripts/publish.py <slug>              # 記事（ai-lab CPT）
    python3 scripts/publish.py --resource <slug>   # 資料（resource CPT）

前提:
    - .env に WP_BASE_URL / WP_USERNAME / WP_APP_PASSWORD 設定済み
    - WordPress で ai-lab / resource カスタム投稿タイプ作成済み
    - pip install -r scripts/requirements.txt 実行済み
"""

import argparse
import base64
import os
import re
import shutil
import sys
from pathlib import Path

try:
    import markdown as md_lib
    import requests
    from dotenv import load_dotenv
except ImportError as e:
    print(f"必要なパッケージが未インストール: {e}", file=sys.stderr)
    print("実行: pip install -r scripts/requirements.txt", file=sys.stderr)
    sys.exit(1)

# ===== 設定 =====

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DRAFTS_DIR = PROJECT_ROOT / "drafts"
PUBLISHED_DIR = PROJECT_ROOT / "published"
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"

# ===== マーカー解析 =====

MARKER_PATTERN = re.compile(r"^===(\w+)===\s*$", re.MULTILINE)


def parse_markers(content: str) -> dict:
    """===XXX=== マーカーで区切られた Markdown を dict に分解"""
    parts = {}
    current_key = None
    current_lines = []

    for line in content.splitlines():
        m = MARKER_PATTERN.match(line)
        if m:
            if current_key:
                parts[current_key] = "\n".join(current_lines).strip()
            current_key = m.group(1)
            current_lines = []
        elif current_key:
            current_lines.append(line)

    if current_key:
        parts[current_key] = "\n".join(current_lines).strip()

    required = ["TITLE", "SLUG", "META", "BODY"]
    for key in required:
        if key not in parts:
            raise ValueError(f"必須マーカー '{key}' が見つかりません")

    return parts


# ===== Markdown → SWELL HTML 変換 =====

SPECIAL_MARKER_PATTERN = re.compile(r"\{\{(mark|point|caution):([^}]+)\}\}")
FAQ_QA_PATTERN = re.compile(
    r"^###\s+Q:\s+(.+?)\n+A:\s+(.+?)(?=\n###\s+Q:|\n##|\Z)",
    re.MULTILINE | re.DOTALL,
)
CODE_BLOCK_PATTERN = re.compile(
    r"<pre><code(?:\s+class=\"language-(\w+)\")?>(.*?)</code></pre>",
    re.DOTALL,
)


def apply_special_markers(html: str) -> str:
    """{{mark:}} {{point:}} {{caution:}} を SWELL HTML に変換"""

    def replacer(match):
        kind = match.group(1)
        text = match.group(2).strip()
        if kind == "mark":
            return f'<span class="swl-marker mark_yellow"><strong>{text}</strong></span>'
        if kind == "point":
            return f'<p class="is-style-big_icon_point">{text}</p>'
        if kind == "caution":
            return f'<p class="is-style-big_icon_caution">{text}</p>'
        return match.group(0)

    return SPECIAL_MARKER_PATTERN.sub(replacer, html)


def apply_faq_blocks(markdown_body: str) -> str:
    """### Q: 質問 + A: 回答 の並びを SWELL FAQ ブロックに変換（Markdown段階で処理）"""

    def build_faq(matches):
        items = []
        for q, a in matches:
            items.append(
                f'<div class="swell-block-faq__item">'
                f'<h3 class="faq_q">{q.strip()}</h3>'
                f'<div class="faq_a"><p>{a.strip()}</p></div>'
                f"</div>"
            )
        return (
            '<div class="swell-block-faq is-style-faq-border" '
            'data-q="fill-main" data-a="col-main">\n'
            + "\n".join(items)
            + "\n</div>"
        )

    # FAQ section（## FAQ 以降の ### Q: ... を全部集める）
    faq_section_pattern = re.compile(
        r"(## FAQ\n+)((?:###\s+Q:.+?(?=\n###\s+Q:|\n##|\Z))+)",
        re.DOTALL,
    )

    def section_replacer(match):
        heading = match.group(1)
        section_body = match.group(2)
        qa_matches = FAQ_QA_PATTERN.findall(section_body)
        if not qa_matches:
            return match.group(0)
        return heading + build_faq(qa_matches)

    return faq_section_pattern.sub(section_replacer, markdown_body)


def convert_code_blocks_to_hcb(html: str) -> str:
    """<pre><code class="language-xxx">...</code></pre> を HCB 形式に変換"""

    def replacer(match):
        lang = match.group(1) or "plain"
        code = match.group(2)
        return (
            f'<div class="hcb_wrap"><pre class="prism line-numbers lang-{lang}">'
            f"<code>{code}</code></pre></div>"
        )

    return CODE_BLOCK_PATTERN.sub(replacer, html)


def convert_lists_to_swell(html: str) -> str:
    """標準 <ul> を SWELL の class 付き ul に変換"""
    return html.replace("<ul>", '<ul class="wp-block-list -list-under-dashed">')


def markdown_to_swell_html(body_md: str) -> str:
    """Markdown 本文を SWELL HTML に変換"""
    # FAQ処理（Markdown段階で、HTMLへ変換する前にSWELLブロック化）
    body_md = apply_faq_blocks(body_md)

    # Markdown → HTML
    html = md_lib.markdown(
        body_md,
        extensions=["fenced_code", "tables", "nl2br", "attr_list"],
    )

    # SWELL特有のマーカー適用
    html = apply_special_markers(html)

    # コードブロック → HCB形式
    html = convert_code_blocks_to_hcb(html)

    # リスト → SWELL クラス付き
    html = convert_lists_to_swell(html)

    return html


# ===== WordPress REST API =====


class WPClient:
    def __init__(self, base_url: str, username: str, app_password: str):
        self.base_url = base_url.rstrip("/")
        token = base64.b64encode(
            f"{username}:{app_password}".encode("utf-8")
        ).decode("ascii")
        self.headers = {
            "Authorization": f"Basic {token}",
            "User-Agent": "note-content-publisher/1.0",
        }

    def upload_media(self, file_path: Path) -> dict:
        """画像をアップロードしてメディア情報を返す"""
        url = f"{self.base_url}/wp-json/wp/v2/media"
        with open(file_path, "rb") as f:
            resp = requests.post(
                url,
                headers={
                    **self.headers,
                    "Content-Disposition": f'attachment; filename="{file_path.name}"',
                    "Content-Type": "image/png",
                },
                data=f.read(),
                timeout=60,
            )
        resp.raise_for_status()
        return resp.json()

    def create_post(self, cpt: str, payload: dict) -> dict:
        url = f"{self.base_url}/wp-json/wp/v2/{cpt}"
        resp = requests.post(
            url,
            headers={**self.headers, "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()


# ===== 画像アップロード&置換 =====

IMAGE_PATTERN = re.compile(r'!\[([^\]]*)\]\((screenshots/[^)]+)\)')


def upload_and_replace_images(body_md: str, wp: WPClient) -> tuple[str, int]:
    """Markdown内の screenshots/ 画像をアップロードして URL 置換"""
    uploaded = 0
    errors = []

    def replacer(match):
        nonlocal uploaded, errors
        alt = match.group(1)
        rel_path = match.group(2)
        abs_path = PROJECT_ROOT / rel_path

        if not abs_path.exists():
            errors.append(f"画像ファイルが見つからない: {rel_path}")
            return match.group(0)

        try:
            media = wp.upload_media(abs_path)
            url = media.get("source_url", "")
            if not url:
                errors.append(f"アップロード失敗: {rel_path}")
                return match.group(0)
            uploaded += 1
            return f'![{alt}]({url})'
        except Exception as e:
            errors.append(f"アップロードエラー {rel_path}: {e}")
            return match.group(0)

    new_body = IMAGE_PATTERN.sub(replacer, body_md)

    if errors:
        print("⚠️ 画像アップロードで一部エラー:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)

    return new_body, uploaded


# ===== メイン処理 =====


def find_draft_file(slug: str, is_resource: bool) -> Path:
    """drafts/配下から対象ファイルを探す"""
    base = DRAFTS_DIR / "resources" if is_resource else DRAFTS_DIR

    # slug 単独 or YYYYMMDD_slug.md のパターンを探す
    candidates = (
        list(base.glob(f"{slug}.md"))
        + list(base.glob(f"*_{slug}.md"))
        + list(base.glob(f"{slug}_*.md"))
    )

    # pages/ の固定ページもチェック
    if not is_resource:
        candidates += list((DRAFTS_DIR / "pages").glob(f"{slug}.md"))

    if not candidates:
        raise FileNotFoundError(
            f"ドラフトファイルが見つかりません: slug={slug} (resource={is_resource})"
        )

    if len(candidates) > 1:
        print(
            f"⚠️ 複数のファイルが該当します。最初の1つを使います: {candidates[0]}",
            file=sys.stderr,
        )

    return candidates[0]


def move_to_published(file_path: Path) -> Path:
    """drafts/ から published/ へファイル移動"""
    relative = file_path.relative_to(DRAFTS_DIR)
    target_dir = PUBLISHED_DIR / relative.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / file_path.name
    shutil.move(str(file_path), str(target))
    return target


def main():
    parser = argparse.ArgumentParser(description="Publish Markdown draft to WordPress")
    parser.add_argument("slug", help="記事のスラッグ（ファイル名の一部）")
    parser.add_argument(
        "--resource",
        action="store_true",
        help="資料（drafts/resources/配下）として扱う",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="変換のみで WordPress には投稿しない（確認用）",
    )
    args = parser.parse_args()

    # .env 読み込み
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv(PROJECT_ROOT / "scripts" / ".env.example")
        print(
            "⚠️ .env が見つかりません。scripts/.env.example をコピーして設定してください",
            file=sys.stderr,
        )

    wp_base = os.environ.get("WP_BASE_URL", "")
    wp_user = os.environ.get("WP_USERNAME", "")
    wp_pass = os.environ.get("WP_APP_PASSWORD", "")
    cpt_article = os.environ.get("WP_CPT_ARTICLE", "ai-lab")
    cpt_resource = os.environ.get("WP_CPT_RESOURCE", "resource")

    if not args.dry_run and not all([wp_base, wp_user, wp_pass]):
        print("❌ .env に WP_BASE_URL / WP_USERNAME / WP_APP_PASSWORD を設定してください", file=sys.stderr)
        sys.exit(1)

    # ファイル探索
    draft_path = find_draft_file(args.slug, args.resource)
    print(f"📄 Markdown: {draft_path}")

    # Markdown 読み込み
    content = draft_path.read_text(encoding="utf-8")
    parts = parse_markers(content)

    title = parts["TITLE"]
    slug = parts["SLUG"]
    meta = parts["META"]
    body_md = parts["BODY"]
    tags_str = parts.get("TAGS", "")

    print(f"📝 タイトル: {title}")
    print(f"🔗 スラッグ: {slug}")
    print(f"📋 メタ（{len(meta)}字）: {meta[:60]}...")

    # WP クライアント（画像アップ用）
    wp = None
    uploaded = 0
    if not args.dry_run:
        wp = WPClient(wp_base, wp_user, wp_pass)
        body_md, uploaded = upload_and_replace_images(body_md, wp)
        print(f"🖼️  画像アップロード: {uploaded}枚")

    # Markdown → SWELL HTML
    html = markdown_to_swell_html(body_md)
    print(f"🔧 HTML変換完了（{len(html)}字）")

    if args.dry_run:
        print("\n=== DRY RUN モード ===")
        print("WordPress への投稿はしません。変換結果:\n")
        print(html[:500])
        print("...")
        return

    # タグ処理
    tags = [t.strip() for t in tags_str.split(",") if t.strip()]

    # WP投稿データ
    cpt = cpt_resource if args.resource else cpt_article
    payload = {
        "title": title,
        "slug": slug,
        "content": html,
        "status": "draft",  # ★絶対に publish にしない
        "excerpt": meta,
    }
    if args.resource:
        payload["password"] = os.environ.get("RESOURCE_PASSWORD", "")

    print(f"📤 WordPress へ投稿中（post_type={cpt}, status=draft）...")
    result = wp.create_post(cpt, payload)

    post_id = result.get("id")
    edit_url = f"{wp_base}/wp-admin/post.php?post={post_id}&action=edit"
    print(f"✅ 投稿完了")
    print(f"   ID: {post_id}")
    print(f"   編集URL: {edit_url}")

    # drafts/ → published/ 移動
    new_path = move_to_published(draft_path)
    print(f"📦 移動完了: {new_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
