#!/usr/bin/env python3
"""站点级产物与资源裁剪：sitemap.xml、robots.txt、图片 alt 回填、mermaid 按页裁剪。

全部是纯函数：输入字符串或路径，输出字符串，不做 IO 之外的副作用。
"""

from __future__ import annotations

import html as html_mod
import re
import subprocess
from pathlib import Path

_IMG_TAG_RE = re.compile(r"<img\b[^>]*>")
_SRC_RE = re.compile(r'\bsrc="([^"]*)"')
_ALT_RE = re.compile(r'\balt="[^"]*"')

# mdBook 的 hash_files 会给脚本名插入 8 位十六进制 hash，两种形态都要容忍
_MERMAID_SCRIPTS_RE = re.compile(
    r'[ \t]*<script src="[^"]*/mermaid(?:-init)?(?:-[0-9a-fA-F]+)?\.(?:min\.)?js"></script>[ \t]*\n?'
)

_MERMAID_MARKER = 'class="mermaid"'

_SITEMAP_XMLNS = "http://www.sitemaps.org/schemas/sitemap/0.9"


# ============================================================
# 图片 alt
# ============================================================


def fill_image_alt(doc: str, alt_map: dict) -> str:
    """按 src 的文件名回填 alt，已有非空 alt 的图不动。

    mdBook 0.5 的 zoomable images 把一张图渲染成两个 <img>（外层一个、放大弹层一个），
    一次回填正好同时修好两处。
    """
    if not alt_map:
        return doc

    def _replace(match: re.Match) -> str:
        tag = match.group(0)
        src = _SRC_RE.search(tag)
        if not src:
            return tag
        alt = alt_map.get(Path(src.group(1)).name)
        if not alt:
            return tag
        existing = _ALT_RE.search(tag)
        if existing and existing.group(0) != 'alt=""':
            return tag
        escaped = html_mod.escape(alt, quote=True)
        if existing:
            return tag.replace(existing.group(0), f'alt="{escaped}"', 1)
        closing = "/>" if tag.endswith("/>") else ">"
        return f'{tag[: -len(closing)]} alt="{escaped}"{closing}'

    return _IMG_TAG_RE.sub(_replace, doc)


# ============================================================
# mermaid 按页裁剪
# ============================================================


def needs_mermaid(doc: str) -> bool:
    """mdbook-mermaid 把 ```mermaid 代码块渲染成 <pre class="mermaid">。"""
    return _MERMAID_MARKER in doc


def prune_mermaid(doc: str) -> str:
    """删掉页面里的 mermaid 脚本引用。

    主库与 init 必须一起删——只删主库会让 init 脚本报错。
    """
    return _MERMAID_SCRIPTS_RE.sub("", doc)


# ============================================================
# sitemap / robots
# ============================================================


def build_sitemap(entries: list[tuple[str, str]], indent: str = "  ") -> str:
    """生成 sitemap.xml。

    lastmod 取不到就整行省略——错误的日期比没有日期更伤信任；
    changefreq 一律不写，Google 已明确忽略。
    """
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<urlset xmlns="{_SITEMAP_XMLNS}">',
    ]
    for url, lastmod in entries:
        lines.append(f"{indent}<url>")
        lines.append(f"{indent * 2}<loc>{html_mod.escape(url)}</loc>")
        if lastmod:
            lines.append(f"{indent * 2}<lastmod>{lastmod}</lastmod>")
        lines.append(f"{indent}</url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def build_robots(site_url: str) -> str:
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /toc.html\n"
        "Disallow: /404.html\n"
        "\n"
        f"Sitemap: {site_url}sitemap.xml\n"
    )


# ============================================================
# git
# ============================================================


def git_lastmod(repo_root: Path, path: str) -> str:
    """取某个源文件的最后提交日期（YYYY-MM-DD）。取不到返回空串。

    依赖完整历史：CI 的 actions/checkout 默认 fetch-depth: 1，
    那样所有文件都会退化成同一个日期。
    """
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", path],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return ""
    return result.stdout.strip()
