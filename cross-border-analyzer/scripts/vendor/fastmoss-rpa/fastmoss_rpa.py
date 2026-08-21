#!/usr/bin/env python3
"""FastMoss — unified single-entry CLI for the consolidated FastMoss skill.

Replaces the 7 separate per-board scripts with one command:

    fastmoss_rpa.py scrape     --section <products|creators|shops|ads|creatives|livestreams>
                           [--ranking <key>] [--url <custom>] --pages N --out CSV
    fastmoss_rpa.py filter     --section <...> [--ranking <key>]
                           [--country L,L] [--category L,L] [--shop-type L,L] [--time L]
                           --pages N --out CSV
    fastmoss_rpa.py analyze    <products|creators|shops|ads|creatives|livestreams|market> [section args] --out-md MD
    fastmoss_rpa.py market     <distribution|base|sales-chart|filter-info> [args]

Transport is BrowserSkill (bsk). All scraping requires an authenticated
Chrome session already open via the BrowserSkill extension.
"""

import argparse
import sys
from pathlib import Path

# Make sibling modules importable regardless of CWD.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import core          # noqa: E402
import analyze       # noqa: E402
import market_api    # noqa: E402


USAGE = """\
FastMoss 统一技能入口

子命令:
  scrape    抓取单个榜单（无筛选）
  filter    带国家/品类/时间筛选抓取
  analyze   生成多维度分析 MD 报告
  market    调用 FastMoss 品类大盘 API（distribution/base/sales-chart/filter-info）

示例:
  python fastmoss_rpa.py scrape --section products --pages 5 --out out/products.csv
  python fastmoss_rpa.py scrape --section creators --ranking fans --pages 5 --out out/fans.csv
  python fastmoss_rpa.py filter --section products --category 美妆个护,女装与女士内衣 --pages 3 --out out/by_category.csv
  python fastmoss_rpa.py filter --section creators --ranking fans --country 美国,印度尼西亚 --pages 3 --out out/fans_by_country.csv
  python fastmoss_rpa.py analyze creators --fans out/fans.csv --out-md out/creators_report.md
  python fastmoss_rpa.py market distribution --region US,ID,TH --time month --out out/categories.csv
"""


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(USAGE)
        return
    sub, rest = argv[0], argv[1:]
    if sub == "scrape":
        core.main(["scrape"] + rest)
    elif sub == "filter":
        core.main(["filter"] + rest)
    elif sub == "analyze":
        analyze.main(rest)
    elif sub == "market":
        market_api.main(rest)
    else:
        print(f"未知子命令: {sub}\n")
        print(USAGE)
        sys.exit(2)


if __name__ == "__main__":
    main()
