#!/usr/bin/env python3
"""按评分模型对规范化后的商品数据打分排名。

用法:
    python3 score.py <normalized.csv> <output.csv>

输出在输入列基础上追加各维度分、三个综合分和异常标记。
权重常量在本文件顶部，与 references/scoring.md 保持一致。
"""

import argparse
import csv
import os
import sys


# 综合潜力分权重（可调，对应 references/scoring.md）
WEIGHTS = {
    "sales_growth": 0.30,
    "price_band": 0.20,
    "commission": 0.15,
    "competition": 0.15,
    "lifecycle": 0.10,
    "shop_quality": 0.10,
}

# 平价价格带（美元），对应美国时尚配件 / 平价饰品
PRICE_LOW = 5.0
PRICE_HIGH = 25.0
PRICE_IDEAL = (PRICE_LOW + PRICE_HIGH) / 2


def f(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def normalize_minmax(values, cap=100.0):
    vals = [v for v in values if v is not None]
    if not vals:
        return {}
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return {v: 60.0 for v in vals}
    return {v: 40.0 + 60.0 * (v - lo) / (hi - lo) for v in vals}


def price_score(price):
    if price is None:
        return 60.0
    if PRICE_LOW <= price <= PRICE_HIGH:
        return 100.0
    if price < 1:
        return 35.0
    if price < PRICE_LOW:
        return 60.0
    if price <= PRICE_HIGH * 2:
        return 70.0
    return 40.0


def commission_score(rate):
    if rate is None:
        return 60.0
    return min(100.0, max(0.0, rate * 5.0))


def lifecycle_score(days):
    if days is None:
        return 60.0
    if days <= 30:
        return 100.0
    if days <= 90:
        return 85.0
    if days <= 180:
        return 65.0
    return 50.0


def shop_score(rating):
    if rating is None:
        return 60.0
    if rating > 5:
        rating = rating / 20.0 * 5.0  # 兼容 100 分制
    return min(100.0, max(0.0, rating / 5.0 * 100.0))


def main():
    ap = argparse.ArgumentParser(description="商品评分")
    ap.add_argument("input", help="规范化 CSV")
    ap.add_argument("output", help="输出评分 CSV")
    args = ap.parse_args()

    if not os.path.isfile(args.input):
        sys.exit(f"输入文件不存在: {args.input}")

    with open(args.input, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    if not rows:
        sys.exit("输入为空，无数据可评分")

    prices = [f(r.get("price")) for r in rows]
    sales7 = [f(r.get("sales7")) for r in rows]
    totals = [f(r.get("sales_total")) for r in rows]
    price_map = normalize_minmax(prices)
    heat_map = normalize_minmax([s for s in sales7 if s is not None] or [0])

    # 竞争度：同品类在榜商品数越多，分数越低
    cat_counts = {}
    for r in rows:
        c = (r.get("category") or "").strip()
        cat_counts[c] = cat_counts.get(c, 0) + 1

    for r in rows:
        price = f(r.get("price"))
        s7 = f(r.get("sales7"))
        total = f(r.get("sales_total"))
        rate = f(r.get("commission"))
        days = f(r.get("listed_days"))
        rating = f(r.get("rating"))
        cat = (r.get("category") or "").strip()

        ps = price_score(price)
        # 销量与增长：热度（周期销量排名）+ 动量（周期销量占总销量比例）
        momentum = (s7 / total) if (s7 is not None and total and total > 0) else None
        mom_map = normalize_minmax([m for m in
                                    [(s7 / t) if (s7 is not None and t and t > 0) else None
                                     for s7, t in zip(sales7, totals)] if m is not None] or [0])
        if s7 is None:
            gs = 50.0
        else:
            heat = heat_map.get(s7, 60.0)
            mom = mom_map.get(momentum, 50.0)
            gs = 0.6 * heat + 0.4 * mom

        cs = commission_score(rate)
        ls = lifecycle_score(days)
        ss = shop_score(rating)
        count = cat_counts.get(cat, 1)
        comp = min(100.0, max(20.0, 100.0 - (count - 1) * 8)) if cat else 60.0

        components = {
            "sales_growth": gs, "price_band": ps, "commission": cs,
            "competition": comp, "lifecycle": ls, "shop_quality": ss,
        }
        wsum = sum(WEIGHTS[k] for k in components)
        potential = sum(WEIGHTS[k] * components[k] for k in components) / wsum
        market_heat = 0.7 * gs + 0.3 * ls
        viability = 0.35 * ps + 0.25 * cs + 0.2 * comp + 0.2 * ss

        markers = []
        if gs >= 80 and (days is not None and days <= 60):
            markers.append("暴涨新星")
        if comp <= 40 and ps >= 90:
            markers.append("价格战红海")
        if cs >= 80 and market_heat >= 70:
            markers.append("高佣爆款")
        if potential >= 80:
            markers.append("高潜力")
        if viability <= 30:
            markers.append("谨慎")

        r["price_score"] = f"{ps:.1f}"
        r["growth_score"] = f"{gs:.1f}"
        r["commission_score"] = f"{cs:.1f}"
        r["competition_score"] = f"{comp:.1f}"
        r["lifecycle_score"] = f"{ls:.1f}"
        r["shop_score"] = f"{ss:.1f}"
        r["market_heat"] = f"{market_heat:.1f}"
        r["viability"] = f"{viability:.1f}"
        r["potential"] = f"{potential:.1f}"
        r["markers"] = ";".join(markers)

    rows.sort(key=lambda r: f(r.get("potential")) or 0, reverse=True)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    fieldnames = list(rows[0].keys())
    with open(args.output, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"已生成: {args.output}（{len(rows)} 个商品，已按综合潜力降序）")


if __name__ == "__main__":
    main()
