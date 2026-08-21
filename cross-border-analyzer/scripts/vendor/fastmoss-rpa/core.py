"""Generic FastMoss table-ranking engine (unified skill core).

Every FastMoss *table* board (products / creators / shops / ads / creatives /
livestreams) is the same paginating scraper with a different configuration
(ranking URLs, the row parser, the output fields, the supported filter
dimensions). This module drives all of them from the config in `sections.py`,
so the scraping logic lives in exactly one place.

Two parse modes (per `sections.SECTIONS[...]["parse_kind"]`):
  - "fixed"     : products — reads raw tr/td, fixed schema, products_parse_row.
  - "headers"   : creators / shops — reads thead headers + tbody rows dynamically.
  - "headers_entity" : ads / creatives / livestreams — like headers, plus an
                        entity-name column resolved from a per-ranking header.

Transport (call / evaluate / session_stop) comes from bridge_browserskill.
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

from bridge_browserskill import call, evaluate, session_stop
from sections import (
    SECTIONS,
    get_entity_header,
)

# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def scrape_current(cfg, session, entity_header=""):
    """Extract + parse the current page using the section's extractor/parser."""
    res = evaluate(cfg["extract_js"], session)
    if "error" in res:
        return [], res

    if cfg["parse_kind"] == "fixed":
        rows = [cfg["parse_row"](c) for c in res.get("rows", [])]
    else:  # headers / headers_entity
        headers = res.get("headers", [])
        rows = []
        for cells in res.get("rows", []):
            if cfg["parse_kind"] == "headers":
                rows.append(cfg["parse_row"](headers, cells))
            else:  # headers_entity
                rows.append(cfg["parse_row"](headers, cells, entity_header))
    return [r for r in rows if r], res


def build_fields(cfg, all_rows):
    """Field order = section base_fields (+ 'ranking' for dynamic) + dynamic extras."""
    base = list(cfg["base_fields"])
    seen = set(base)
    extra = []
    for r in all_rows:
        for k in r.keys():
            if k not in seen:
                extra.append(k)
                seen.add(k)
    return base + extra


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------------------
# Plain scrape (no filter)
# ---------------------------------------------------------------------------


def scrape_table(section, ranking_key=None, url=None, pages=5, out=None,
                 session=None, nav_sleep=None, page_sleep=3.5):
    cfg = SECTIONS[section]
    session = session or cfg["group_title"]
    nav_sleep = nav_sleep if nav_sleep is not None else cfg.get("nav_sleep", 6.0)

    if cfg["mode"] == "fixed":
        url = url or cfg.get("url")
        ranking_key = None
        entity_header = ""
    else:
        if not ranking_key and not url:
            print("ERROR: --ranking or --url is required for this section")
            sys.exit(2)
        url = url or cfg["rankings"][ranking_key]
        ranking_key = ranking_key or "custom"
        entity_header = get_entity_header(section, ranking_key) if cfg["parse_kind"] == "headers_entity" else ""

    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    nav = call("navigate", {"url": url, "newTab": True, "group_title": cfg["group_title"]}, session)
    print(f"[navigate] {nav.get('data', nav)}")
    time.sleep(nav_sleep)

    all_rows = []
    headers_seen = None
    for i in range(pages):
        rows, meta = scrape_current(cfg, session, entity_header)
        if not headers_seen and "headers" in meta:
            headers_seen = meta["headers"]
            print(f"[page {i + 1}] headers: {headers_seen}")
        print(f"[page {i + 1}] rows={len(rows)} title={meta.get('title', '')[:50]}")
        for r in rows:
            r["page"] = i + 1
            if ranking_key:
                r["ranking"] = ranking_key
            all_rows.append(r)
        if i < pages - 1:
            click = evaluate(cfg["next_page_js"], session)
            if not click.get("clicked"):
                print(f"[page {i + 1}] next button not found, stopping")
                break
            time.sleep(page_sleep)

    if not all_rows:
        print("NO ROWS SCRAPED")
        sys.exit(1)

    fields = build_fields(cfg, all_rows)
    write_csv(out_path, all_rows, fields)
    print(f"[done] {len(all_rows)} rows -> {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Filtered scrape
# ---------------------------------------------------------------------------
#
# products supports ONE of: country / category / shop_type (single dim per run)
# dynamic boards (creators/shops/ads/creatives/livestreams) support country,
# and creators additionally supports an optional single time window.

FILTER_BASE_FIELDS = {
    "products": ["filter"],                       # + PRODUCTS_FIELDS
    "creators": ["page", "ranking", "filter_country", "filter_time",
                 "rank", "creator_name", "creator_id", "creator_category", "country"],
    "shops": ["page", "ranking", "filter_country", "rank",
              "shop_name", "shop_legal_name", "shop_category", "shop_rating"],
    "ads": ["page", "ranking", "filter_country", "rank", "entity_name"],
    "creatives": ["page", "ranking", "filter_country", "rank", "entity_name"],
    "livestreams": ["page", "ranking", "filter_country", "rank", "entity_name"],
}


def _click_filter(template, label, session):
    return evaluate(template % json.dumps(label, ensure_ascii=False), session)


def scrape_filtered_products(dim, labels, pages, out, session, nav_sleep, page_sleep):
    cfg = SECTIONS["products"]
    session = session or cfg["group_title"]
    nav_sleep = nav_sleep if nav_sleep is not None else cfg.get("nav_sleep", 6.0)
    template = cfg["click_templates"][dim]

    combined_path = Path(out)
    per_label_dir = combined_path.parent
    per_label_dir.mkdir(parents=True, exist_ok=True)
    all_rows = []
    for label in labels:
        call("navigate", {"url": cfg["url"], "newTab": False}, session)
        time.sleep(nav_sleep)
        click = _click_filter(template, label, session)
        print(f"[{label}] click: {click}")
        time.sleep(nav_sleep)
        rows_out = []
        for p in range(pages):
            res = evaluate(cfg["extract_js"], session)
            if "error" in res:
                print(f"[{label} page {p + 1}] {res}")
                continue
            parsed = [cfg["parse_row"](c) for c in res.get("rows", [])]
            parsed = [r for r in parsed if r]
            if p == 0 and parsed:
                sample_key = {"country": "country", "category": "category"}.get(dim, "country")
                vals = {r.get(sample_key, "") for r in parsed}
                print(f"[{label} page {p + 1}] rows={len(parsed)} {sample_key}s={vals}")
            else:
                print(f"[{label} page {p + 1}] rows={len(parsed)}")
            for r in parsed:
                r["filter"] = label
                r["page"] = p + 1
                rows_out.append(r)
            if p < pages - 1:
                evaluate(cfg["next_page_js"], session)
                time.sleep(page_sleep)
        if rows_out:
            fields = ["filter"] + cfg["base_fields"]
            out_path = per_label_dir / f"{combined_path.stem}_{label}{combined_path.suffix}"
            write_csv(out_path, rows_out, fields)
            print(f"[{label}] saved {len(rows_out)} -> {out_path}")
            all_rows.extend(rows_out)

    if all_rows:
        fields = ["filter"] + cfg["base_fields"]
        write_csv(combined_path, all_rows, fields)
        print(f"[combined] {len(all_rows)} -> {combined_path}")


def scrape_filtered_dynamic(section, ranking_key, country_labels, time_label,
                            pages, out, session, nav_sleep, page_sleep):
    cfg = SECTIONS[section]
    session = session or cfg["group_title"]
    nav_sleep = nav_sleep if nav_sleep is not None else cfg.get("nav_sleep", 6.0)
    url = cfg["rankings"][ranking_key]
    entity_header = get_entity_header(section, ranking_key) if cfg["parse_kind"] == "headers_entity" else ""
    country_tpl = cfg["click_templates"]["country"]
    time_tpl = cfg["click_templates"].get("time")

    combined_path = Path(out)
    per_run_dir = combined_path.parent
    per_run_dir.mkdir(parents=True, exist_ok=True)

    all_rows = []
    headers_seen = None
    for country in country_labels:
        call("navigate", {"url": url, "newTab": False}, session)
        time.sleep(nav_sleep)
        if time_label and time_tpl:
            click = _click_filter(time_tpl, time_label, session)
            print(f"[{ranking_key}/{country}/{time_label}] time click: {click}")
            time.sleep(nav_sleep)
        if country:
            click = _click_filter(country_tpl, country, session)
            print(f"[{ranking_key}/{country}/{time_label}] country click: {click}")
            time.sleep(nav_sleep)
        rows_out = []
        for p in range(pages):
            rows, meta = scrape_current(cfg, session, entity_header)
            if not headers_seen and "headers" in meta:
                headers_seen = meta["headers"]
            if p == 0 and rows:
                key = "shop_category" if section == "shops" else "country"
                vals = {r.get(key, "") for r in rows}
                print(f"[{ranking_key}/{country} page {p + 1}] rows={len(rows)} {key}s={vals}")
            else:
                print(f"[{ranking_key}/{country} page {p + 1}] rows={len(rows)}")
            for r in rows:
                r["filter_country"] = country or "(default)"
                if time_label:
                    r["filter_time"] = time_label
                r["ranking"] = ranking_key
                r["page"] = p + 1
                rows_out.append(r)
            if p < pages - 1:
                evaluate(cfg["next_page_js"], session)
                time.sleep(page_sleep)
        if rows_out and len(country_labels) > 1:
            suffix = country or "all"
            out_path = per_run_dir / f"{combined_path.stem}_{suffix}{combined_path.suffix}"
            write_csv(out_path, rows_out, FILTER_BASE_FIELDS[section])
            print(f"[{country or 'all'}] saved {len(rows_out)} -> {out_path}")
        all_rows.extend(rows_out)

    if all_rows:
        write_csv(combined_path, all_rows, FILTER_BASE_FIELDS[section])
        print(f"[combined] {len(all_rows)} -> {combined_path}")


def run_filter(section, country=None, category=None, shop_type=None, time=None,
               ranking_key=None, pages=3, out=None, session=None,
               nav_sleep=None, page_sleep=3.5):
    """Entry point for the `filter` subcommand."""
    if section == "products":
        if country:
            dim, labels = "country", country
        elif category:
            dim, labels = "category", category
        elif shop_type:
            dim, labels = "shop_type", shop_type
        else:
            print("ERROR: products filter requires --country / --category / --shop-type")
            sys.exit(2)
        scrape_filtered_products(dim, labels, pages, out, session, nav_sleep, page_sleep)
    else:
        if not ranking_key:
            print(f"ERROR: --ranking is required for {section} filter")
            sys.exit(2)
        scrape_filtered_dynamic(section, ranking_key, country, time, pages, out,
                                session, nav_sleep, page_sleep)


# ---------------------------------------------------------------------------
# CLI (scrape / filter only — analyze & market live in fastmoss_rpa.py)
# ---------------------------------------------------------------------------


def _add_common_args(p):
    p.add_argument("--pages", type=int, default=5, help="Number of pages to scrape (default: 5)")
    p.add_argument("--out", required=True, help="Output CSV path")
    p.add_argument("--session", help="Browser session name (default: section group_title)")
    p.add_argument("--nav-sleep", type=float, default=None, help="Seconds after navigation")
    p.add_argument("--page-sleep", type=float, default=3.5, help="Seconds between pages (default: 3.5)")


def main(argv=None):
    p = argparse.ArgumentParser(description="FastMoss unified table engine",
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("scrape", help="Scrape one ranking (no filter)")
    sp.add_argument("--section", required=True, choices=list(SECTIONS.keys()))
    sp.add_argument("--ranking", help="Ranking key (dynamic sections). Mutually exclusive with --url")
    sp.add_argument("--url", help="Custom FastMoss URL (overrides --ranking)")
    _add_common_args(sp)

    fp = sub.add_parser("filter", help="Scrape with a country/category/time filter")
    fp.add_argument("--section", required=True, choices=list(SECTIONS.keys()))
    fp.add_argument("--ranking", help="Ranking key (required for dynamic sections)")
    fp.add_argument("--country", help="Comma-separated country labels")
    fp.add_argument("--category", help="Comma-separated category labels (products only)")
    fp.add_argument("--shop-type", help="Comma-separated shop-type labels (products only)")
    fp.add_argument("--time", help="Time-window label, e.g. 周榜 (creators only)")
    fp.add_argument("--pages", type=int, default=3, help="Pages per filter combination (default: 3)")
    fp.add_argument("--out", required=True, help="Combined output CSV path")
    fp.add_argument("--session", help="Browser session name")
    fp.add_argument("--nav-sleep", type=float, default=None)
    fp.add_argument("--page-sleep", type=float, default=3.5)

    args = p.parse_args(argv)

    if args.cmd == "scrape":
        scrape_table(args.section, ranking_key=args.ranking, url=args.url,
                     pages=args.pages, out=args.out, session=args.session,
                     nav_sleep=args.nav_sleep, page_sleep=args.page_sleep)
    elif args.cmd == "filter":
        country = [s.strip() for s in args.country.split(",") if s.strip()] if args.country else None
        category = [s.strip() for s in args.category.split(",") if s.strip()] if args.category else None
        shop_type = [s.strip() for s in args.shop_type.split(",") if s.strip()] if args.shop_type else None
        run_filter(args.section, country=country, category=category, shop_type=shop_type,
                   time=args.time or None, ranking_key=args.ranking, pages=args.pages,
                   out=args.out, session=args.session, nav_sleep=args.nav_sleep,
                   page_sleep=args.page_sleep)


if __name__ == "__main__":
    main()
