#!/usr/bin/env python3
"""规范化 FastMoss / 用户导入的 CSV 为统一列结构。

用法:
    python3 normalize.py <input.csv> <output.csv>

输出 UTF-8 BOM CSV（Excel 直接打开不乱码）。无法识别的列原样保留。
"""

import argparse
import csv
import os
import re
import sys
from datetime import date


CANONICAL = [
    "rank", "name", "price", "sales7", "gmv7", "sales_total", "gmv_total",
    "commission", "listed_days", "shop", "category", "rating", "reviews",
    "sales_growth", "image",
]

OPTIONAL = {"image"}

ALIASES = {
    "rank": ["排名", "rank", "ranking", "序号", "top"],
    "name": ["商品名", "商品名称", "商品标题", "product_name", "name", "title", "product name"],
    "price": ["价格", "价格(usd)", "price", "售价", "price_usd"],
    "sales7": ["周期销量", "周期销量(件)", "7天销量", "近7天销量", "销量(7天)",
               "sales_period", "三日销量", "月销量", "sales", "7d sales",
               "weekly sales", "周销量"],
    "gmv7": ["周期gmv", "7天gmv", "近7天gmv", "gmv_period", "三日销售额",
             "月销售额", "gmv", "7d gmv", "weekly gmv", "周期销售额"],
    "sales_total": ["总销量", "累计销量", "total_sales", "total sales", "total sold", "销量"],
    "gmv_total": ["总gmv", "累计gmv", "total_gmv", "total gmv"],
    "commission": ["佣金率", "佣金", "commission", "commission rate", "达人佣金"],
    "listed_days": ["上架天数", "上架时间", "上架日期", "listed_at", "listing days", "listed at",
                    "created at", "上架"],
    "shop": ["店铺", "店铺名", "店铺名称", "shop", "store"],
    "category": ["品类", "类目", "category", "一级类目", "二级类目"],
    "rating": ["评分", "店铺评分", "商品评分", "rating", "score"],
    "reviews": ["评论数", "评论", "评价数", "reviews", "review count"],
    "sales_growth": ["销量增长率", "周期销量增长", "近7天销量增长率", "环比",
                     "sales_growth", "growth"],
    "image": ["图片", "商品图", "商品图片", "图片地址", "图片链接", "图片url",
              "image", "img", "img_src", "image_url", "product image",
              "缩略图", "thumbnail"],
}


def detect_encoding(path):
    for enc in ("utf-8-sig", "utf-8", "gbk", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                f.read(4096)
            return enc
        except (UnicodeDecodeError, OSError):
            continue
    return "latin-1"


def sniff_delimiter(path, enc):
    with open(path, "r", encoding=enc, newline="") as f:
        sample = f.read(8192)
    try:
        return csv.Sniffer().sniff(sample, delimiters=",\t;|").delimiter
    except csv.Error:
        return ","


def parse_num(value):
    if value is None:
        return ""
    s = str(value).strip()
    if s in ("", "-", "--", "—", "NA", "N/A", "null", "None"):
        return ""
    s = s.replace(",", "").replace("$", "").replace("¥", "").replace("%", "")
    mult = 1
    if "亿" in s:
        mult, s = 100_000_000, s.replace("亿", "")
    elif "万" in s:
        mult, s = 10_000, s.replace("万", "")
    elif "K" in s or "k" in s:
        mult, s = 1_000, s.replace("K", "").replace("k", "")
    elif "M" in s or "m" in s:
        mult, s = 1_000_000, s.replace("M", "").replace("m", "")
    # 区间值（10-20、9.90 - 12.90、8–20、10~20、10万-20万）取中值，避免被当缺失
    m = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*[-~–—至]\s*(-?\d+(?:\.\d+)?)\s*$", s)
    if m:
        return str(round((float(m.group(1)) + float(m.group(2))) / 2 * mult, 2))
    if re.search(r"[^\d.\-eE+]", s):
        return ""
    try:
        return str(round(float(s) * mult, 2))
    except ValueError:
        return ""


def _selftest():
    cases = {
        "10-20": "15.0",
        "9.90 - 12.90": "11.4",
        "8–20": "14.0",
        "10~20": "15.0",
        "10万-20万": "150000.0",
        "-5": "-5.0",
        "10-15%": "12.5",
        "2026-08-22": "",
        "12": "12.0",
    }
    for raw, want in cases.items():
        got = parse_num(raw)
        assert got == want, f"parse_num({raw!r}) = {got!r}, want {want!r}"
    print("parse_num selftest OK")


def parse_days(value):
    """上架天数：数字直接返回；日期按距今天数计算。"""
    s = str(value or "").strip()
    if not s or s in ("-", "--", "—"):
        return ""
    m = re.match(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", s)
    if m:
        try:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return str(max((date.today() - date(y, mo, d)).days, 0))
        except ValueError:
            return ""
    return parse_num(s)


def map_columns(header):
    normalized = {c.lower().strip() for c in header}
    mapping = {}
    for canon in CANONICAL:
        for alias in ALIASES[canon]:
            key = alias.lower().strip()
            if key in normalized:
                idx = next(i for i, h in enumerate(header)
                           if h.lower().strip() == key)
                mapping[canon] = idx
                break
    return mapping


def main():
    ap = argparse.ArgumentParser(description="规范化 CSV 列")
    ap.add_argument("input", nargs="?", help="输入 CSV")
    ap.add_argument("output", nargs="?", help="输出 CSV")
    ap.add_argument("--selftest", action="store_true",
                    help="运行 parse_num 自检后退出")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return
    if not args.input or not args.output:
        ap.error("input 和 output 必填（或使用 --selftest）")

    if not os.path.isfile(args.input):
        sys.exit(f"输入文件不存在: {args.input}")
    enc = detect_encoding(args.input)
    delim = sniff_delimiter(args.input, enc)

    with open(args.input, "r", encoding=enc, newline="") as f:
        reader = csv.reader(f, delimiter=delim)
        header = next(reader)
        mapping = map_columns(header)
        rows = list(reader)

    # 未知列原样透传：规范列之后按原始顺序追加（同名加后缀避免重复）
    mapped_idx = set(mapping.values())
    extra = []
    extra_names = set()
    for i, h in enumerate(header):
        if i in mapped_idx or not h.strip():
            continue
        name = h.strip()
        if name in extra_names:
            n, base = 2, name
            while f"{base}_{n}" in extra_names:
                n += 1
            name = f"{base}_{n}"
        extra_names.add(name)
        extra.append((i, name))

    fieldnames = CANONICAL + [h for _, h in extra] + ["source"]
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        for row in rows:
            out = {c: "" for c in CANONICAL}
            for canon, idx in mapping.items():
                val = row[idx] if idx < len(row) else ""
                if canon in ("price", "sales7", "gmv7", "sales_total", "gmv_total",
                             "commission", "rating", "reviews", "sales_growth"):
                    val = parse_num(val)
                elif canon == "listed_days":
                    val = parse_days(val)
                out[canon] = val.strip()
            for i, name in extra:
                out[name] = row[i].strip() if i < len(row) else ""
            out["source"] = os.path.basename(args.input)
            writer.writerow([out.get(n, "") for n in fieldnames])

    missing = [c for c in CANONICAL if c not in mapping and c not in OPTIONAL]
    print(f"已生成: {args.output}（{len(rows)} 行）")
    if extra:
        print(f"原样保留的额外列: {', '.join(n for _, n in extra)}")
    if missing:
        print(f"未匹配的规范列: {', '.join(missing)}（原列保留在 source 对应的原始行）")


if __name__ == "__main__":
    main()
