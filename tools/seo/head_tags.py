#!/usr/bin/env python3
"""head 标签注入：description / canonical / Open Graph / Twitter Card / JSON-LD。

只做确定性的字符串替换，不做 HTML 解析。所有函数都必须幂等——
先剥掉上一次注入的标记块再重新注入，重复运行产出完全相同的字节。
"""

from __future__ import annotations

import html as html_mod
import json
import re
from dataclasses import dataclass, field
from urllib.parse import quote

MARKER_BEGIN = "<!-- seo:begin -->"
MARKER_END = "<!-- seo:end -->"

# 连同 marker 前的行首缩进一起吃掉：否则剥掉块后缩进会残留，
# 每跑一次就多累积一层，幂等性立刻崩掉。
_MARKER_BLOCK_RE = re.compile(
    r"[ \t]*" + re.escape(MARKER_BEGIN) + r".*?" + re.escape(MARKER_END) + r"\n?", re.S
)
_LANG_RE = re.compile(r'<html lang="[^"]*"')
_DESCRIPTION_RE = re.compile(r'<meta name="description" content="[^"]*">')
_HEAD_END_RE = re.compile(r"(?P<indent>[ \t]*)</head>")
_MAIN_RE = re.compile(r"<main[^>]*>(.*?)</main>", re.S)
_P_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")

_ROBOTS_META = '<meta name="robots" content="noindex">'

# 各站长平台的验证 meta 名，与 site.toml 里 [verification] 的键一一对应
_VERIFICATION_META = {
    "google": "google-site-verification",
    "bing": "msvalidate.01",
    "baidu": "baidu-site-verification",
}


@dataclass
class SiteConfig:
    site_url: str
    book_title: str
    author: str
    language: str
    locale: str
    default_description: str
    og_image: str = ""
    verification: dict = field(default_factory=dict)


@dataclass
class PageContext:
    rel_path: str
    kind: str  # index | chapter | 404
    title: str
    description: str
    url: str
    lastmod: str = ""


# ============================================================
# 幂等注入原语
# ============================================================


def strip_marker_block(doc: str) -> str:
    return _MARKER_BLOCK_RE.sub("", doc)


def inject_marker_block(doc: str, payload: str) -> str:
    """把标签块插到 </head> 前一行，缩进与 </head> 对齐。"""
    doc = strip_marker_block(doc)
    match = _HEAD_END_RE.search(doc)
    if not match:
        return doc
    indent = match.group("indent")
    block = "\n".join(indent + line if line else line for line in payload.splitlines())
    return f"{doc[: match.start()]}{block}\n{indent}</head>{doc[match.end() :]}"


def set_language(doc: str, language: str) -> str:
    return _LANG_RE.sub(f'<html lang="{language}"', doc, count=1)


def replace_description(doc: str, description: str) -> str:
    """替换已有的 meta description，绝不追加，避免页面上出现第二个。"""
    escaped = html_mod.escape(description, quote=True)
    return _DESCRIPTION_RE.sub(
        f'<meta name="description" content="{escaped}">', doc, count=1
    )


def ensure_noindex(doc: str) -> str:
    if 'name="robots"' in doc:
        return doc
    return inject_marker_block(doc, _ROBOTS_META)


def absolute_url(site_url: str, rel_path: str) -> str:
    """拼绝对地址。中文文件名必须按段百分号编码，quote 默认不转义分隔符 /。"""
    if not rel_path:
        return site_url
    encoded = "/".join(quote(segment, safe="") for segment in rel_path.split("/"))
    return site_url + encoded


# ============================================================
# 文案提取
# ============================================================


def extract_summary(doc: str, limit: int = 150) -> str:
    """从正文首段取一段摘要，作为 pages.toml 未覆盖时的回退。"""
    main = _MAIN_RE.search(doc)
    if not main:
        return ""
    for para in _P_RE.findall(main.group(1)):
        text = _WS_RE.sub(" ", html_mod.unescape(_TAG_RE.sub("", para)).replace("\u3000", " ")).strip()
        if len(text) >= 30:
            return _truncate(text, limit)
    return ""


def _truncate(text: str, limit: int) -> str:
    """在句读边界截断，找不到合适边界就硬截。"""
    if len(text) <= limit:
        return text
    window = text[:limit]
    for punct in ("。", "！", "？", "；"):
        index = window.rfind(punct)
        if index >= limit // 2:
            return window[: index + 1]
    return window


def chapter_title_of(page_title: str, book_title: str) -> str:
    """mdBook 的 <title> 形如 "章节名 - 书名"，og:title 只留章节名。"""
    suffix = f" - {book_title}"
    return page_title[: -len(suffix)] if page_title.endswith(suffix) else page_title


# ============================================================
# 组装
# ============================================================


def process_page(doc: str, page: PageContext, site: SiteConfig, og_image_exists: bool) -> str:
    """组装函数：只按顺序调用上面各步，不实现细节。"""
    doc = set_language(doc, site.language)
    if page.kind == "404":
        return ensure_noindex(doc)
    doc = replace_description(doc, page.description)
    return inject_marker_block(doc, _build_head_payload(page, site, og_image_exists))


def _build_head_payload(page: PageContext, site: SiteConfig, og_image_exists: bool) -> str:
    title = chapter_title_of(page.title, site.book_title) or site.book_title
    book_title = html_mod.escape(site.book_title, quote=True)
    escaped_title = html_mod.escape(title, quote=True)
    escaped_desc = html_mod.escape(page.description, quote=True)
    escaped_url = html_mod.escape(page.url, quote=True)

    lines = [
        MARKER_BEGIN,
        f'<link rel="canonical" href="{escaped_url}">',
        f'<meta property="og:type" content="{"website" if page.kind == "index" else "article"}">',
        f'<meta property="og:site_name" content="{book_title}">',
        f'<meta property="og:locale" content="{site.locale}">',
        f'<meta property="og:title" content="{escaped_title}">',
        f'<meta property="og:description" content="{escaped_desc}">',
        f'<meta property="og:url" content="{escaped_url}">',
        f'<meta name="twitter:card" content="{"summary_large_image" if og_image_exists else "summary"}">',
        f'<meta name="twitter:title" content="{escaped_title}">',
        f'<meta name="twitter:description" content="{escaped_desc}">',
    ]

    # 分享图缺失时整组省略，绝不让卡片指向一个 404
    if og_image_exists:
        image_url = absolute_url(site.site_url, site.og_image)
        lines += [
            f'<meta property="og:image" content="{image_url}">',
            '<meta property="og:image:width" content="1200">',
            '<meta property="og:image:height" content="630">',
            f'<meta name="twitter:image" content="{image_url}">',
        ]

    lines += _verification_metas(site)
    lines += _jsonld_scripts(page, site)
    lines.append(MARKER_END)
    return "\n".join(lines)


def _verification_metas(site: SiteConfig) -> list[str]:
    out = []
    for key, meta_name in _VERIFICATION_META.items():
        code = str((site.verification or {}).get(key, "")).strip()
        if code:
            escaped = html_mod.escape(code, quote=True)
            out.append(f'<meta name="{meta_name}" content="{escaped}">')
    return out


# ============================================================
# JSON-LD 结构化数据
# ============================================================


def _jsonld_scripts(page: PageContext, site: SiteConfig) -> list[str]:
    if page.kind == "index":
        return [_ld_script(_website_ld(site)), _ld_script(_book_ld(site))]
    if page.kind == "chapter":
        return [_ld_script(_article_ld(page, site)), _ld_script(_breadcrumb_ld(page, site))]
    return []


def _ld_script(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    # 转义 < 防止正文里的 </script> 逃逸出标签
    payload = payload.replace("<", "\\u003c")
    return f'<script type="application/ld+json">{payload}</script>'


def _author_ld(site: SiteConfig) -> dict:
    return {"@type": "Person", "name": site.author}


def _website_ld(site: SiteConfig) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": site.book_title,
        "url": site.site_url,
        "inLanguage": site.language,
        "author": _author_ld(site),
    }


def _book_ld(site: SiteConfig) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Book",
        "name": site.book_title,
        "url": site.site_url,
        "inLanguage": site.language,
        "author": _author_ld(site),
        "bookFormat": "https://schema.org/EBook",
        "isAccessibleForFree": True,
    }


def _article_ld(page: PageContext, site: SiteConfig) -> dict:
    data = {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": chapter_title_of(page.title, site.book_title),
        "description": page.description,
        "url": page.url,
        "inLanguage": site.language,
        "author": _author_ld(site),
        "isPartOf": {
            "@type": "Book",
            "name": site.book_title,
            "url": site.site_url,
        },
    }
    if page.lastmod:
        data["dateModified"] = page.lastmod
    return data


def _breadcrumb_ld(page: PageContext, site: SiteConfig) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": site.book_title,
                "item": site.site_url,
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": chapter_title_of(page.title, site.book_title),
                "item": page.url,
            },
        ],
    }
