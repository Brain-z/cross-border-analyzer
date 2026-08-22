#!/usr/bin/env python3
"""从评分后的 CSV 生成 Markdown 分析报告。

用法:
    python3 report.py <scored.csv> <output.md> [--query "美国 时尚配饰 近7天 销量榜"]
"""

import argparse
import csv
import os
import statistics
import sys
from datetime import datetime


def f(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def fmt_num(v):
    if v is None:
        return "-"
    if v >= 10000:
        return f"{v / 10000:.1f}万"
    if v == int(v):
        return f"{int(v):,}"
    return f"{v:,.2f}"


def main():
    ap = argparse.ArgumentParser(description="生成 Markdown 分析报告")
    ap.add_argument("input", help="评分后 CSV")
    ap.add_argument("output", help="输出 report.md")
    ap.add_argument("--query", default="", help="用户需求复述")
    args = ap.parse_args()

    if not os.path.isfile(args.input):
        sys.exit(f"输入文件不存在: {args.input}")
    with open(args.input, "r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        sys.exit("输入为空，无法生成报告")

    prices = [f(r.get("price")) for r in rows if f(r.get("price")) is not None]
    sales = [f(r.get("sales7")) for r in rows if f(r.get("sales7")) is not None]
    commissions = [f(r.get("commission")) for r in rows
                   if f(r.get("commission")) is not None]
    cats = {}
    for r in rows:
        c = (r.get("category") or "未知").strip() or "未知"
        cats[c] = cats.get(c, 0) + 1
    markers = {}
    for r in rows:
        for m in (r.get("markers") or "").split(";"):
            if m:
                markers[m] = markers.get(m, 0) + 1

    lines = []
    lines.append("# 跨境商品分析报告")
    lines.append("")
    lines.append(f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    if args.query:
        lines.append(f"- 需求：{args.query}")
    lines.append(f"- 数据文件：{os.path.basename(args.input)}")
    lines.append(f"- 商品数：{len(rows)}")
    lines.append("")

    lines.append("## 市场概览")
    lines.append("")
    if prices:
        lines.append(f"- 价格区间：{fmt_num(min(prices))} – {fmt_num(max(prices))} 美元"
                     f"，中位数 {fmt_num(statistics.median(prices))} 美元")
    if sales:
        lines.append(f"- 周期销量合计：{fmt_num(sum(sales))}，单品中位数 {fmt_num(statistics.median(sales))}")
    if commissions:
        lines.append(f"- 平均佣金率：{statistics.mean(commissions):.1f}%")
    top_cats = ", ".join(
        f"{c} {n}款" for c, n in sorted(cats.items(), key=lambda x: -x[1])[:5]
    )
    lines.append(f"- 品类分布：{top_cats}")
    if markers:
        lines.append(f"- 标记统计：{', '.join(f'{m} {n}' for m, n in markers.items())}")
    lines.append("")

    lines.append("## Top 10 综合潜力榜")
    lines.append("")
    lines.append("| # | 商品 | 价格($) | 周期销量 | 佣金率 | 热度 | 可做性 | 潜力 | 标记 |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    top = sorted(rows, key=lambda r: f(r.get("potential")) or 0, reverse=True)[:10]
    for i, r in enumerate(top, 1):
        name = (r.get("name") or "未知")[:30]
        price = f(r.get("price"))
        s7 = f(r.get("sales7"))
        comm = f(r.get("commission"))
        heat = f(r.get("market_heat"))
        via = f(r.get("viability"))
        pot = f(r.get("potential"))
        mk = (r.get("markers") or "-").replace(";", "、") or "-"
        lines.append(f"| {i} | {name} | {fmt_num(price)} | {fmt_num(s7)} | "
                     f"{fmt_num(comm)}{'%' if comm is not None else ''} | "
                     f"{fmt_num(heat)} | {fmt_num(via)} | {fmt_num(pot)} | {mk} |")
    lines.append("")

    lines.append("## 选品建议（按可做性排序 Top 5）")
    lines.append("")
    lines.append("| # | 商品 | 价格($) | 可做性 | 理由 |")
    lines.append("|---|---|---|---|---|")
    for i, r in enumerate(sorted(rows, key=lambda x: f(x.get("viability")) or 0,
                                 reverse=True)[:5], 1):
        name = (r.get("name") or "未知")[:30]
        price = f(r.get("price"))
        via = f(r.get("viability"))
        reasons = []
        if (r.get("markers") or "").find("高佣") >= 0:
            reasons.append("佣金率高")
        if f(r.get("price_score")) and f(r.get("price_score")) >= 90:
            reasons.append("价格带契合平价饰品")
        if f(r.get("competition_score")) and f(r.get("competition_score")) >= 80:
            reasons.append("同类竞争相对少")
        if not reasons:
            reasons.append("综合得分靠前")
        lines.append(f"| {i} | {name} | {fmt_num(price)} | {fmt_num(via)} | {'、'.join(reasons)} |")
    lines.append("")

    lines.append("## 风险提示")
    lines.append("")
    danger = [r for r in rows if (r.get("markers") or "").find("谨慎") >= 0]
    red = [r for r in rows if (r.get("markers") or "").find("价格战红海") >= 0]
    if red:
        lines.append(f"- 价格战红海 {len(red)} 款：同品类在榜商品密集且集中在平价区间，"
                     f"上新需有差异化。")
    if danger:
        lines.append(f"- 谨慎 {len(danger)} 款：可做性得分低（价格带偏离、佣金低或竞争高）。")
    if not danger and not red:
        lines.append("- 当前样本未发现明显风险信号，仍建议关注上架时间和竞品密度。")
    lines.append("")

    lines.append("## 数据说明")
    lines.append("")
    lines.append("- 数据来自 FastMoss 榜单抓取或用户导入，原始 CSV 保留在 `data/` 可回溯；")
    lines.append("- 评分权重与规则见插件 `references/scoring.md`，可自行调整；")
    lines.append("- 指标缺失时该项按中性分处理，不影响其他维度。")
    lines.append("")

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"已生成: {args.output}")


if __name__ == "__main__":
    main()
