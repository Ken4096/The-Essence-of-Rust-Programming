#!/usr/bin/env python3
"""幂等性自检：把后处理重跑一遍，产出必须零字节差异。

这是本方案唯一的硬性回归约束——后处理每跑一次就多叠一层标签，
是这类方案最常见的翻车方式。

用 Python 而不是 md5sum/diff：Windows 的 make 由 cmd.exe 执行 recipe，
那里没有那群 unix 工具，本地与 CI 就没法共用同一条命令了。

用法：
    python tools/seo/verify.py --web-dir web [--git-lastmod]
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import postprocess  # noqa: E402

# 后处理会写出的站点级产物，随 html 一起纳入比对
_PRODUCTS = ("sitemap.xml", "robots.txt")


def _digest(web_dir: Path) -> dict[str, str]:
    """对每个产物算摘要。

    读字节而非文本：按文本读会把 CRLF/LF 归一化，正好掩盖掉一类真实差异。
    """
    files = sorted(web_dir.glob("*.html")) + [web_dir / name for name in _PRODUCTS]
    return {p.name: hashlib.md5(p.read_bytes()).hexdigest() for p in files if p.is_file()}


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    web_dir = Path(args.web_dir).resolve()
    if not web_dir.is_dir():
        print(f"错误：构建输出目录不存在：{web_dir}", file=sys.stderr)
        return 1

    before = _digest(web_dir)
    if not before:
        print(f"错误：{web_dir} 下没有可校验的产物", file=sys.stderr)
        return 1

    passthrough = ["--web-dir", str(web_dir)]
    if args.git_lastmod:
        passthrough.append("--git-lastmod")
    if postprocess.main(passthrough) != 0:
        return 1

    after = _digest(web_dir)
    changed = sorted(
        name
        for name in set(before) | set(after)
        if before.get(name) != after.get(name)
    )
    if changed:
        print(f"幂等性失败：二次运行改变了 {len(changed)} 个产物", file=sys.stderr)
        for name in changed:
            print(f"  {name}", file=sys.stderr)
        return 1

    print(f"幂等性通过：{len(before)} 个产物二次运行零字节差异")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验 SEO 后处理的幂等性")
    parser.add_argument("--web-dir", default="web", help="mdBook 构建输出目录（默认 web）")
    parser.add_argument(
        "--git-lastmod",
        action="store_true",
        help="让二次运行与首次运行取同样的 lastmod",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
