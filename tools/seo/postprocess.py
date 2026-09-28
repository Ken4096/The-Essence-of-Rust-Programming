#!/usr/bin/env python3
"""SEO 后处理入口。

在 `mdbook build` 之后运行，把 SEO 标签与站点级产物注入到构建输出里。
每页该写什么全部来自本目录下的 *.toml，本脚本只做机械替换：
新增章节时改数据文件即可，不需要改代码。

用法：
    python tools/seo/postprocess.py --web-dir web [--site-url URL] [--git-lastmod] [--verbose]

幂等性：重复运行必须产出完全相同的字节。这是本方案唯一的硬性回归约束，
CI 里用 `git diff --exit-code -- web/` 守住。
"""

from __future__ import annotations

import argparse
import html
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import head_tags  # noqa: E402
import site_files  # noqa: E402

SEO_DIR = Path(__file__).resolve().parent
REPO_ROOT = SEO_DIR.parent.parent

# toc.html 是侧边栏 iframe 的 fallback，mdBook 已给它 noindex，不参与任何处理
SKIP_PAGES = {"toc.html"}

_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    web_dir = Path(args.web_dir).resolve()
    if not web_dir.is_dir():
        print(f"错误：构建输出目录不存在：{web_dir}", file=sys.stderr)
        return 1

    site = _load_site(SEO_DIR / "site.toml", args.site_url)
    descriptions = _load_table(SEO_DIR / "pages.toml", "pages")
    alt_map = _load_table(SEO_DIR / "img-alt.toml", "images")
    og_image_exists = bool(site.og_image) and (web_dir / site.og_image).is_file()

    pages = sorted(p for p in web_dir.glob("*.html") if p.name not in SKIP_PAGES)
    if not pages:
        print(f"错误：{web_dir} 下没有可处理的 html", file=sys.stderr)
        return 1

    sitemap_entries: list[tuple[str, str]] = []
    for path in pages:
        kind = _page_kind(path.name)
        source_md = _source_md(path.name)
        doc = path.read_text(encoding="utf-8")

        lastmod = (
            site_files.git_lastmod(REPO_ROOT, f"src/{source_md}")
            if args.git_lastmod
            else ""
        )
        page = head_tags.PageContext(
            rel_path=path.name,
            kind=kind,
            title=_title_of(doc),
            description=_description_for(doc, source_md, descriptions, site),
            url=_canonical_url(site.site_url, path.name, kind),
            lastmod=lastmod,
        )

        doc = head_tags.process_page(doc, page, site, og_image_exists)
        doc = site_files.fill_image_alt(doc, alt_map)
        if not site_files.needs_mermaid(doc):
            doc = site_files.prune_mermaid(doc)
        path.write_text(doc, encoding="utf-8")

        if _in_sitemap(path.name, kind):
            sitemap_entries.append((page.url, lastmod))

        if args.verbose:
            print(f"  {path.name}")

    (web_dir / "sitemap.xml").write_text(
        site_files.build_sitemap(sitemap_entries), encoding="utf-8"
    )
    (web_dir / "robots.txt").write_text(
        site_files.build_robots(site.site_url), encoding="utf-8"
    )

    if args.verbose:
        print(f"处理页面 {len(pages)} 个，sitemap 收录 {len(sitemap_entries)} 条")
        if not og_image_exists:
            print(f"提示：分享图 {site.og_image} 不存在，已省略整组 og:image 标签")
    return 0


# ============================================================
# 页面判定
# ============================================================


def _page_kind(name: str) -> str:
    if name == "index.html":
        return "index"
    if name == "404.html":
        return "404"
    return "chapter"


def _source_md(name: str) -> str:
    """产物名 -> 源文件名。站点根页面渲染的就是前言那一章。"""
    if name == "index.html":
        return "introduction.md"
    return f"{Path(name).stem}.md"


def _canonical_url(site_url: str, name: str, kind: str) -> str:
    """站点根与前言页内容逐字节相同，两者必须指向同一个规范地址。"""
    if kind == "index" or name == "introduction.html":
        return site_url
    return head_tags.absolute_url(site_url, name)


def _in_sitemap(name: str, kind: str) -> bool:
    """只收录 canonical URL。

    introduction.html 的 canonical 指向站点根，因此不进 sitemap。
    """
    if kind == "index":
        return True
    if kind != "chapter":
        return False
    return name != "introduction.html"


# ============================================================
# 数据加载
# ============================================================


def _load_site(path: Path, site_url_override: str | None) -> head_tags.SiteConfig:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    site_url = site_url_override or data["site_url"]
    return head_tags.SiteConfig(
        site_url=site_url if site_url.endswith("/") else site_url + "/",
        book_title=data["book_title"],
        author=data["author"],
        language=data["language"],
        locale=data["locale"],
        default_description=data["default_description"],
        og_image=data.get("og_image", ""),
        verification=data.get("verification", {}),
    )


def _load_table(path: Path, table: str) -> dict:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return data.get(table, {})


def _description_for(
    doc: str, source_md: str, descriptions: dict, site: head_tags.SiteConfig
) -> str:
    """回退链：手写映射表 -> 正文首段摘要 -> 站点兜底描述。

    中间那一层保证新增章节即使忘记补数据，也不会退化成"全站同一句话"。
    """
    if source_md in descriptions:
        return descriptions[source_md]
    return head_tags.extract_summary(doc) or site.default_description


def _title_of(doc: str) -> str:
    match = _TITLE_RE.search(doc)
    return html.unescape(match.group(1).strip()) if match else ""


# ============================================================
# CLI
# ============================================================


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="为 mdBook 构建输出注入 SEO 标签与站点产物")
    parser.add_argument("--web-dir", default="web", help="mdBook 构建输出目录（默认 web）")
    parser.add_argument("--site-url", default=None, help="覆盖 tools/seo/site.toml 里的站点域名")
    parser.add_argument(
        "--git-lastmod",
        action="store_true",
        help="用 git log 取每章的真实修改日期作为 sitemap 的 lastmod",
    )
    parser.add_argument("--verbose", action="store_true", help="逐页打印处理结果")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
