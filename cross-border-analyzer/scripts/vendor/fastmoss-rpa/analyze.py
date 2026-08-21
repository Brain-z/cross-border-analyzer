"""Unified FastMoss report engine.

Ports the 7 original per-board analyze.py scripts into one module, dispatched
by the first positional arg (--section equivalent). Each section:
  products / creators / shops / ads / creatives / livestreams / market

Reports are rendered from the templates in references/reports/<section>.md
(copied verbatim from each original analysis_recipe.md), so the placeholder
names are identical to the originals.
"""

import argparse
import csv
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = SKILL_ROOT / "references" / "reports"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def read_csv(path):
    if not path or not Path(path).exists():
        return []
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def pct(n, total):
    return f"{n * 100 // total}%" if total else "-"


def breakdown(rows, key, top_n=10):
    cnt = Counter(r.get(key, "").strip() for r in rows if r.get(key, "").strip())
    total = sum(cnt.values())
    return {"total": total, "rows": cnt.most_common(top_n)}


def cross_tab(rows, row_key, col_key, top_n=3):
    out = defaultdict(Counter)
    for r in rows:
        rk = r.get(row_key, "").strip()
        ck = r.get(col_key, "").strip()
        if rk and ck:
            out[rk][ck] += 1
    return out


def _render(section, stats, out_path):
    template = (REPORTS_DIR / f"{section}.md").read_text(encoding="utf-8")
    content = template.format(**stats)
    out_path.write_text(content, encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# products
# ---------------------------------------------------------------------------


def top_breakdown(rows, key, top_n=8, label=None):
    cnt = Counter(r[key] for r in rows if r.get(key, "").strip())
    total = sum(cnt.values())
    return {"label": label or key, "total": total, "rows": cnt.most_common(top_n)}


def country_category_crosstab(rows):
    out = defaultdict(Counter)
    for r in rows:
        out[r.get("filter", "")][r.get("category", "")] += 1
    return out


def category_country_crosstab(rows):
    out = defaultdict(Counter)
    for r in rows:
        out[r.get("filter", "")][r.get("country", "")] += 1
    return out


def repeat_shops(rows, min_count=2):
    shops = Counter(r["shop"] for r in rows if r.get("shop", "").strip())
    return [(s, c) for s, c in shops.most_common() if c >= min_count]


def shop_cadence(rows):
    months = Counter(r["listed_at"][:7] for r in rows if r.get("listed_at", ""))
    return dict(sorted(months.items(), reverse=True))


def analyze_products(args):
    top50 = read_csv(args.top50)
    by_country = read_csv(args.by_country)
    by_category = read_csv(args.by_category)
    shop = []
    for path in args.shop:
        shop.extend(read_csv(path))

    stats_raw = {
        "top50_breakdown": {
            "country": top_breakdown(top50, "country", label="country"),
            "category": top_breakdown(top50, "category", label="category"),
            "commission": top_breakdown(top50, "commission", label="commission"),
        },
        "country_category": country_category_crosstab(by_country),
        "category_country": category_country_crosstab(by_category),
        "repeat_shops": repeat_shops(top50),
        "shop_cadence": shop_cadence(shop),
    }

    top = stats_raw["top50_breakdown"]
    country_md = "\n".join(f"| {n} | {c} | {pct(c, top['country']['total'])} |"
                           for n, c in top["country"]["rows"])
    category_md = "\n".join(f"| {n} | {c} |" for n, c in top["category"]["rows"])
    commission_md = "\n".join(f"| {n} | {c} | {pct(c, top['commission']['total'])} |"
                              for n, c in top["commission"]["rows"])
    cc_md = "\n".join(
        f"| {country} | " + " | ".join(f"{cnt}" for cat, cnt in cats.most_common(3)) +
        f" | (total {sum(cats.values())}) |"
        for country, cats in stats_raw["country_category"].items()
    )
    catc_md = "\n".join(
        f"| {cat} | " + " | ".join(f"{cnt}" for ctry, cnt in countries.most_common(3)) +
        f" | (total {sum(countries.values())}) |"
        for cat, countries in stats_raw["category_country"].items()
    )
    rep_md = "\n".join(f"- `{s}` × {c}" for s, c in stats_raw["repeat_shops"]) or "_(none — Top 50 中无重复店铺)_"
    cadence = stats_raw["shop_cadence"]
    cadence_md = "\n".join(f"| {m} | {c} |" for m, c in cadence.items()) or "_(无数据)_"

    today = datetime.now().strftime("%Y-%m-%d")
    n_top = top["country"]["total"]
    n_country = sum(sum(c.values()) for c in stats_raw["country_category"].values())
    n_category = sum(sum(c.values()) for c in stats_raw["category_country"].values())
    n_shop = sum(cadence.values())

    _render("products", {
        "scrape_date": today,
        "sample": f"{n_top} (Top50) + {n_country} (国家筛选) + {n_category} (品类筛选) + {n_shop} (单店铺)",
        "country_table": country_md,
        "category_table": category_md,
        "commission_table": commission_md,
        "country_category_table": cc_md,
        "category_country_table": catc_md,
        "repeat_shops": rep_md,
        "shop_cadence_table": cadence_md,
    }, Path(args.out_md))
    print(f"[done] report -> {args.out_md}")


# ---------------------------------------------------------------------------
# creators / shops / ads / creatives / livestreams (dynamic)
# ---------------------------------------------------------------------------


def top_creators(all_rows, min_count=2):
    seen = Counter()
    for r in all_rows:
        name = r.get("creator_name", "").strip()
        if name:
            seen[name] += 1
    return [(n, c) for n, c in seen.most_common(20) if c >= min_count][:10]


def top_shops(all_rows, min_count=2):
    seen = Counter()
    for r in all_rows:
        name = r.get("shop_name", "").strip()
        if name:
            seen[name] += 1
    return [(n, c) for n, c in seen.most_common(20) if c >= min_count][:10]


def top_entities(all_rows, min_count=2):
    seen = Counter()
    for r in all_rows:
        name = r.get("entity_name", "").strip()
        if name:
            seen[name] += 1
    return [(n, c) for n, c in seen.most_common(20) if c >= min_count][:10]


def _dynamic_stats(per_ranking, breakdown_keys, cross_row, cross_col, top_fn):
    all_rows = []
    for rows in per_ranking.values():
        all_rows.extend(rows)
    for r in all_rows:
        if not r.get("country"):
            r["country"] = r.get("filter_country", "")
    stats = {
        "per_ranking": {k: {"total": len(v)} for k, v in per_ranking.items()},
        "country_breakdown": breakdown(all_rows, "country"),
        "ranking_country": cross_tab(all_rows, "ranking", "country"),
        "repeat": top_fn(all_rows, 2),
    }
    # shops uses category + ranking×shop_category
    if "shop_category" in breakdown_keys:
        stats["category_breakdown"] = breakdown(all_rows, "shop_category")
        stats["ranking_category"] = cross_tab(all_rows, "ranking", "shop_category")
    # creators uses creator_category
    if "creator_category" in breakdown_keys:
        stats["category_breakdown"] = breakdown(all_rows, "creator_category")
    return stats


def _render_dynamic(section, stats, out_path):
    template = (REPORTS_DIR / f"{section}.md").read_text(encoding="utf-8")

    if section == "creators":
        country_md = "\n".join(f"| {n} | {c} | {pct(c, stats['country_breakdown']['total'])} |"
                               for n, c in stats["country_breakdown"]["rows"])
        cat_md = "\n".join(f"| {n} | {c} |" for n, c in stats["category_breakdown"]["rows"])
        rc_rows = [f"| {rk} | {sum(c.values())} | {' | '.join(f'{c}({n})' for c, n in c.most_common(3))} |"
                   for rk, c in stats["ranking_country"].items()]
        repeat_md = "\n".join(f"- `{n}` × {c}" for n, c in stats["repeat"]) or "_(无 — 各榜单均无重复达人)_"
        sample = " + ".join(f"{k}: {v['total']} 条" for k, v in stats["per_ranking"].items() if v["total"])
        content = template.format(
            scrape_date=datetime.now().strftime("%Y-%m-%d"), sample=sample,
            country_table=country_md or "_(无数据)_", category_table=cat_md or "_(无数据)_",
            ranking_country_table="\n".join(rc_rows) or "_(无数据)_", repeat_creators=repeat_md,
        )
    elif section == "shops":
        cat_md = "\n".join(f"| {n} | {c} | {pct(c, stats['category_breakdown']['total'])} |"
                           for n, c in stats["category_breakdown"]["rows"])
        country_md = "\n".join(f"| {n} | {c} | {pct(c, stats['country_breakdown']['total'])} |"
                               for n, c in stats["country_breakdown"]["rows"])
        rc_rows = [f"| {rk} | {sum(cnt.values())} | {' | '.join(f'{c}({n})' for c, n in cnt.most_common(3))} |"
                   for rk, cnt in stats["ranking_category"].items()]
        repeat_md = "\n".join(f"- `{n}` × {c}" for n, c in stats["repeat"]) or "_(无 — 各榜单均无重复店铺)_"
        sample = " + ".join(f"{k}: {v['total']} 条" for k, v in stats["per_ranking"].items() if v["total"])
        content = template.format(
            scrape_date=datetime.now().strftime("%Y-%m-%d"), sample=sample,
            category_table=cat_md or "_(无数据)_", country_table=country_md or "_(无数据)_",
            ranking_category_table="\n".join(rc_rows) or "_(无数据)_", repeat_shops=repeat_md,
        )
    else:  # ads / creatives / livestreams
        country_md = "\n".join(f"| {n} | {c} | {pct(c, stats['country_breakdown']['total'])} |"
                               for n, c in stats["country_breakdown"]["rows"])
        rc_rows = [f"| {rk} | {sum(cnt.values())} | {' | '.join(f'{c}({n})' for c, n in cnt.most_common(3))} |"
                   for rk, cnt in stats["ranking_country"].items()]
        repeat_md = "\n".join(f"- `{n}` × {c}" for n, c in stats["repeat"]) or "_(无 — 各榜单均无重复实体)_"
        sample = " + ".join(f"{k}: {v['total']} 条" for k, v in stats["per_ranking"].items() if v["total"])
        content = template.format(
            scrape_date=datetime.now().strftime("%Y-%m-%d"), sample=sample,
            country_table=country_md or "_(无数据)_",
            ranking_country_table="\n".join(rc_rows) or "_(无数据)_", repeat_entities=repeat_md,
        )
    out_path.write_text(content, encoding="utf-8")
    return out_path


def _split_filtered(combined):
    bucket = defaultdict(list)
    for r in read_csv(combined):
        bucket[r.get("ranking", "unknown")].append(r)
    return bucket


def analyze_creators(args):
    per_ranking_files = {"fans": args.fans, "commerceTop": args.commerce, "blue-v": args.blue_v,
                         "popular": args.popular, "potentialTop": args.horse}
    per_ranking = {k: read_csv(v) for k, v in per_ranking_files.items() if v}
    if args.filtered:
        for k, rows in _split_filtered(args.filtered).items():
            per_ranking.setdefault(k, [])
            per_ranking[k].extend(rows)
    stats = _dynamic_stats(per_ranking, ["creator_category"], "ranking", "country", top_creators)
    _render_dynamic("creators", stats, Path(args.out_md))
    print(f"[done] report -> {args.out_md}")


def analyze_shops(args):
    per_ranking_files = {"sales": args.sales, "hot": args.hot}
    per_ranking = {k: read_csv(v) for k, v in per_ranking_files.items() if v}
    if args.filtered:
        for k, rows in _split_filtered(args.filtered).items():
            per_ranking.setdefault(k, [])
            per_ranking[k].extend(rows)
    stats = _dynamic_stats(per_ranking, ["shop_category"], "ranking", "shop_category", top_shops)
    _render_dynamic("shops", stats, Path(args.out_md))
    print(f"[done] report -> {args.out_md}")


def analyze_ads(args):
    per_ranking_files = {"tag": args.tag, "keyword": args.keyword, "category": args.category}
    per_ranking = {k: read_csv(v) for k, v in per_ranking_files.items() if v}
    if args.filtered:
        for k, rows in _split_filtered(args.filtered).items():
            per_ranking.setdefault(k, [])
            per_ranking[k].extend(rows)
    stats = _dynamic_stats(per_ranking, [], "ranking", "country", top_entities)
    _render_dynamic("ads", stats, Path(args.out_md))
    print(f"[done] report -> {args.out_md}")


def analyze_creatives(args):
    per_ranking_files = {"video": args.video, "song": args.song, "hashtag": args.hashtag}
    per_ranking = {k: read_csv(v) for k, v in per_ranking_files.items() if v}
    if args.filtered:
        for k, rows in _split_filtered(args.filtered).items():
            per_ranking.setdefault(k, [])
            per_ranking[k].extend(rows)
    stats = _dynamic_stats(per_ranking, [], "ranking", "country", top_entities)
    _render_dynamic("creatives", stats, Path(args.out_md))
    print(f"[done] report -> {args.out_md}")


def analyze_livestreams(args):
    per_ranking_files = {"tiktok": args.tiktok, "hotProduct": args.hot_product,
                         "liveCommerce": args.live_commerce}
    per_ranking = {k: read_csv(v) for k, v in per_ranking_files.items() if v}
    if args.filtered:
        for k, rows in _split_filtered(args.filtered).items():
            per_ranking.setdefault(k, [])
            per_ranking[k].extend(rows)
    stats = _dynamic_stats(per_ranking, [], "ranking", "country", top_entities)
    _render_dynamic("livestreams", stats, Path(args.out_md))
    print(f"[done] report -> {args.out_md}")


# ---------------------------------------------------------------------------
# market
# ---------------------------------------------------------------------------


def to_number(s):
    if s is None:
        return 0
    s = str(s).strip().rstrip("%")
    try:
        return float(s)
    except Exception:
        return 0


def analyze_market(args):
    rows = []
    for path in args.distribution:
        rows.extend(read_csv(path))
    if not rows:
        print("NO ROWS. Pass --distribution <path> (repeatable).")
        return

    by_region = defaultdict(list)
    for r in rows:
        by_region[r.get("region") or "(global)"].append(r)

    top_per_region = {}
    for region, items in by_region.items():
        items_sorted = sorted(items, key=lambda r: to_number(r.get("category_sale_amount", 0)), reverse=True)
        top_per_region[region] = [(it.get("category_name", ""),
                                   it.get("category_sale_amount_show", ""),
                                   to_number(it.get("category_sale_amount_mom_rate", 0))) for it in items_sorted]

    growth = []
    for r in rows:
        rate = to_number(r.get("category_sale_amount_mom_rate", 0))
        if rate > 0:
            growth.append((r.get("category_name", ""), r.get("region") or "(global)", int(rate)))
    growth.sort(key=lambda x: x[2], reverse=True)

    cat_region_count = Counter()
    for region, top in top_per_region.items():
        for name, _, _ in top[:5]:
            cat_region_count[name] += 1
    repeats = [(name, c) for name, c in cat_region_count.most_common(20) if c >= 2]

    top_per_region_md = [f"| {region} | {', '.join(f'{name} ({amt})' for name, amt, _ in cats[:5])} |"
                         for region, cats in top_per_region.items()]
    growth_md = [f"| {name} | {region} | {rate}% |" for name, region, rate in growth[:15]]
    rc_md = [f"| {region} | {len(cats)} | {', '.join(name for name, _, _ in cats[:10])} |"
             for region, cats in top_per_region.items()]
    repeat_md = [f"- `{name}` 出现在 {count} 个市场的 Top 5" for name, count in repeats] or \
                ["_(无 — 各市场 Top 5 没有重复品类)_"]

    today = datetime.now().strftime("%Y-%m-%d")
    regions = list(by_region.keys())
    sample = f"region 数: {len(regions)} ({', '.join(regions)})"
    source_str = ", ".join(Path(s).name for s in args.distribution)

    _render("market", {
        "scrape_date": today,
        "sample": sample,
        "source_files": source_str,
        "top_per_region_table": "\n".join(top_per_region_md) or "_(无数据)_",
        "growth_table": "\n".join(growth_md) or "_(无数据)_",
        "region_crosstab_table": "\n".join(rc_md) or "_(无数据)_",
        "cross_region_repeats": "\n".join(repeat_md),
    }, Path(args.out_md))
    print(f"[done] report -> {args.out_md}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv=None):
    p = argparse.ArgumentParser(description="FastMoss unified report engine",
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="section", required=True)

    # products
    sp = sub.add_parser("products")
    sp.add_argument("--top50", help="Top50 / unfiltered ranking CSV")
    sp.add_argument("--by-country", help="by_country CSV")
    sp.add_argument("--by-category", help="by_category CSV")
    sp.add_argument("--shop", action="append", default=[], help="single-shop CSV (repeatable)")
    sp.add_argument("--out-md", required=True)
    sp.set_defaults(func=analyze_products)

    # creators
    sc = sub.add_parser("creators")
    sc.add_argument("--fans"); sc.add_argument("--commerce"); sc.add_argument("--blue-v")
    sc.add_argument("--popular"); sc.add_argument("--horse")
    sc.add_argument("--filtered")
    sc.add_argument("--out-md", required=True)
    sc.set_defaults(func=analyze_creators)

    # shops
    sh = sub.add_parser("shops")
    sh.add_argument("--sales"); sh.add_argument("--hot")
    sh.add_argument("--filtered")
    sh.add_argument("--out-md", required=True)
    sh.set_defaults(func=analyze_shops)

    # ads
    ad = sub.add_parser("ads")
    ad.add_argument("--tag"); ad.add_argument("--keyword"); ad.add_argument("--category")
    ad.add_argument("--filtered")
    ad.add_argument("--out-md", required=True)
    ad.set_defaults(func=analyze_ads)

    # creatives
    cr = sub.add_parser("creatives")
    cr.add_argument("--video"); cr.add_argument("--song"); cr.add_argument("--hashtag")
    cr.add_argument("--filtered")
    cr.add_argument("--out-md", required=True)
    cr.set_defaults(func=analyze_creatives)

    # livestreams
    lv = sub.add_parser("livestreams")
    lv.add_argument("--tiktok"); lv.add_argument("--hot-product"); lv.add_argument("--live-commerce")
    lv.add_argument("--filtered")
    lv.add_argument("--out-md", required=True)
    lv.set_defaults(func=analyze_livestreams)

    # market
    mk = sub.add_parser("market")
    mk.add_argument("--distribution", action="append", default=[], help="categoryDistribution CSV (repeatable)")
    mk.add_argument("--out-md", required=True)
    mk.set_defaults(func=analyze_market)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
