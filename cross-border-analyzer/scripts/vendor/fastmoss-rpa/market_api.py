"""FastMoss market (API-mode) module for the unified skill.

Ports the original fastmoss-market scripts into one module:
  - common.py        -> ensure_market_page / fetch_json / write_csv / write_json / REGION_NAMES
  - fetch_distribution.py -> fetch_distribution()
  - fetch_base.py         -> fetch_base()
  - fetch_sales_chart.py  -> fetch_sales_chart()
  - fetch_filter_info.py  -> fetch_filter_info()

Unlike the table boards, market data comes from FastMoss JSON APIs called via
page-context fetch() (so cookies + origin are shared). The browser is still
driven through BrowserSkill (bsk) — navigate once to the market page, then call
fetch_json for each metric.
"""

import argparse
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from bridge_browserskill import call, evaluate, session_stop

DEFAULT_SESSION = "fastmoss-market"
MARKET_URL = "https://www.fastmoss.com/zh/market/market-category"
ANALYZE_URL = "https://www.fastmoss.com/zh/market/market-analyze"

# Region code -> 中文 label mapping (16 markets).
REGION_NAMES = {
    "US": "美国", "ID": "印度尼西亚", "GB": "英国", "VN": "越南",
    "TH": "泰国", "MY": "马来西亚", "PH": "菲律宾", "ES": "西班牙",
    "MX": "墨西哥", "DE": "德国", "FR": "法国", "IT": "意大利",
    "BR": "巴西", "JP": "日本", "SG": "新加坡", "SA": "沙特",
}


def ensure_market_page(session, page_url=MARKET_URL, sleep_after=4.0):
    call("navigate", {"url": page_url, "newTab": True, "group_title": "fastmoss-market"}, session)
    time.sleep(sleep_after)


_FETCH_JS_TEMPLATE = """
(async () => {
  const url = %URL%;
  const resp = await fetch(url, {credentials: 'include'});
  const text = await resp.text();
  let data;
  try { data = JSON.parse(text); } catch (e) { data = {raw: text.slice(0, 2000)}; }
  return JSON.stringify({status: resp.status, data});
})()
"""


def fetch_json(url_path, session, base="https://www.fastmoss.com"):
    full_url = url_path if url_path.startswith("http") else base + url_path
    sep = "&" if "?" in full_url else "?"
    full_url = f"{full_url}{sep}_time={int(time.time())}&cnonce={int(time.time() * 1000) % 100000000}"
    js = _FETCH_JS_TEMPLATE.replace("%URL%", json.dumps(full_url))
    res = evaluate(js, session)
    if "error" in res:
        return {"_error": res["error"]}
    return res


def write_csv(path, rows, base_fields):
    extra_fields = []
    seen = set(base_fields)
    for r in rows:
        for k in r.keys():
            if k not in seen:
                extra_fields.append(k)
                seen.add(k)
    fields = base_fields + extra_fields
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# fetch_distribution — categoryDistribution (行业格局)
# ---------------------------------------------------------------------------


def _most_recent_completed_month(today=None):
    today = today or datetime.now()
    if today.month == 1:
        return f"{today.year - 1}-12"
    return f"{today.year}-{today.month - 1:02d}"


def _distribution_url(region, time_mode, pcid, date_value=None):
    params = ["is_mock=0"]
    if region:
        params.append(f"region={region}")
    if time_mode == "month":
        dv = date_value or _most_recent_completed_month()
        params.append(f"date_value={dv}")
    if pcid:
        params.append(f"pcid={pcid}")
    return "/api/analysis/V2/categoryDistribution?" + "&".join(params)


def fetch_distribution(region="", time_mode="28d", pcid=None, out=None,
                       raw_json=None, session=DEFAULT_SESSION):
    regions = [r.strip().upper() for r in region.split(",") if r.strip()] if region else [""]
    ensure_market_page(session)
    combined_path = Path(out)
    per_run_dir = combined_path.parent
    per_run_dir.mkdir(parents=True, exist_ok=True)

    all_rows, raw_payloads = [], []
    for reg in regions:
        url = _distribution_url(reg, time_mode, pcid)
        res = fetch_json(url, session)
        label = reg or "global"
        if "_error" in res:
            print(f"[{label}] error: {res['_error']} url={url}")
            continue
        if res.get("status") != 200:
            print(f"[{label}] HTTP {res.get('status')} url={url}")
            continue
        body = res.get("data", {})
        dots = body.get("data", {}).get("dots", [])
        if not dots:
            print(f"[{label}] no dots (url={url})")
            continue
        date_value = _most_recent_completed_month() if time_mode == "month" else ""
        region_name = REGION_NAMES.get(reg, "")
        rows = []
        for d in dots:
            row = dict(d)
            row["region"] = reg
            row["region_name"] = d.get("region_name") or region_name
            row["time_window"] = time_mode
            row["date_value"] = date_value
            rows.append(row)
        print(f"[{label}] {len(rows)} categories (url: {url})")
        if raw_json:
            raw_payloads.append({"region": label, "url": url, "dots": rows})
        if rows and len(regions) > 1:
            out_path = per_run_dir / f"{combined_path.stem}_{label}{combined_path.suffix}"
            write_csv(out_path, rows, _distribution_base_fields())
            print(f"[{label}] saved -> {out_path}")
        all_rows.extend(rows)

    if all_rows:
        write_csv(combined_path, all_rows, _distribution_base_fields())
        print(f"[combined] {len(all_rows)} rows -> {combined_path}")
    if raw_json and raw_payloads:
        write_json(raw_json, raw_payloads)


def _distribution_base_fields():
    return [
        "region", "region_name", "time_window", "date_value",
        "category_id", "category_name",
        "category_sale_amount", "category_sale_amount_show",
        "category_sale_amount_mom_rate", "category_sale_amount_mom_rate_show",
        "cur_sale_amount", "last_sale_amount",
    ]


# ---------------------------------------------------------------------------
# fetch_base — GoodCategory/base (市场总览)
# ---------------------------------------------------------------------------


def fetch_base(region="", action="1", pcid=None, out=None,
               top_products_csv=None, session=DEFAULT_SESSION):
    region = (region or "").strip().upper()
    ensure_market_page(session, page_url=ANALYZE_URL)
    params = []
    if region:
        params.append(f"region={region}")
    params.append(f"action={action}")
    if pcid:
        params.append(f"pcid={pcid}")
    url = "/api/analysis/GoodCategory/base?" + "&".join(params)
    res = fetch_json(url, session)
    if "_error" in res:
        print(f"[error] {res['_error']}")
        sys.exit(1)
    if res.get("status") != 200:
        print(f"[error] HTTP {res.get('status')}: {res}")
        sys.exit(1)
    body = res.get("data", {})
    if body.get("code") != 200:
        print(f"[error] API code {body.get('code')}: {body}")
        sys.exit(1)
    payload = body.get("data", {})
    payload["_region"] = region or "global"
    payload["_region_name"] = REGION_NAMES.get(region, "")
    payload["_url"] = url
    write_json(out, payload)
    print(f"[done] base metrics for region={region or 'global'} -> {out}")
    for k in ["category_name", "category_sold_count_show", "category_sale_amount",
              "category_sale_amount_mom_rate", "category_sale_amount_yoy_rate",
              "product_count", "sales_product_count", "sales_author_count",
              "sales_video_count", "sales_live_count"]:
        if k in payload:
            print(f"  {k}: {payload[k]}")
    top = payload.get("top_products") or []
    print(f"[top_products] {len(top)} items")
    if top_products_csv and top:
        out_csv = Path(top_products_csv)
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        fields = ["region", "rank", "product_id", "title", "sold_count", "sale_amount",
                  "total_sold_count", "total_sale_amount", "sold_count_inc_rate",
                  "aweme_count", "live_count", "author_count", "launch_time"]
        with out_csv.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            for i, p in enumerate(top, 1):
                row = dict(p)
                row["region"] = region or "global"
                row["rank"] = i
                w.writerow(row)
        print(f"[top_products_csv] -> {out_csv}")


# ---------------------------------------------------------------------------
# fetch_sales_chart — GoodCategory/salesChart (日销时序)
# ---------------------------------------------------------------------------


def fetch_sales_chart(region="", action="1", pcid=None, out=None, session=DEFAULT_SESSION):
    region = (region or "").strip().upper()
    ensure_market_page(session, page_url=ANALYZE_URL)
    params = []
    if region:
        params.append(f"region={region}")
    params.append(f"action={action}")
    if pcid:
        params.append(f"pcid={pcid}")
    url = "/api/analysis/GoodCategory/salesChart?" + "&".join(params)
    res = fetch_json(url, session)
    if "_error" in res:
        print(f"[error] {res['_error']}")
        sys.exit(1)
    if res.get("status") != 200:
        print(f"[error] HTTP {res.get('status')}: {res}")
        sys.exit(1)
    body = res.get("data", {})
    if body.get("code") != 200:
        print(f"[error] API code {body.get('code')}: {body}")
        sys.exit(1)
    items = body.get("data", {}).get("list", [])
    rows = []
    for item in items:
        row = dict(item)
        row["region"] = region or "global"
        row["region_name"] = REGION_NAMES.get(region, "")
        rows.append(row)
    print(f"[done] {len(rows)} daily rows for region={region or 'global'} (url: {url})")
    base_fields = ["region", "region_name", "dt", "data_value",
                   "category_sold_count", "category_sold_count_show",
                   "inc_product_count", "inc_product_count_show",
                   "sales_product_count", "sales_product_count_show",
                   "sales_author_count", "sales_author_count_show",
                   "sales_video_count", "sales_video_count_show",
                   "sales_live_count", "sales_live_count_show"]
    write_csv(out, rows, base_fields)
    print(f"[csv] -> {out}")


# ---------------------------------------------------------------------------
# fetch_filter_info — GoodCategory/filterInfo (类目/国家词表)
# ---------------------------------------------------------------------------


def fetch_filter_info(out=None, session=DEFAULT_SESSION):
    ensure_market_page(session)
    res = fetch_json("/api/analysis/GoodCategory/filterInfo", session)
    if "_error" in res:
        print(f"[error] {res['_error']}")
        sys.exit(1)
    if res.get("status") != 200:
        print(f"[error] HTTP {res.get('status')}: {res}")
        sys.exit(1)
    payload = res.get("data", {}).get("data", res.get("data", {}))
    if not isinstance(payload, dict):
        payload = {"raw": res}
    if out:
        write_json(out, payload)
        print(f"[done] {len(payload.get('category', []))} categories, "
              f"{len(payload.get('country', []))} countries -> {out}")
    else:
        for c in payload.get("category", []):
            print(f"  pcid={c.get('c_code'):>3}  {c.get('c_name'):<20}  rank={c.get('rank')}")
        print(f"\n=== {len(payload.get('country', []))} countries ===")
        for c in payload.get("country", []):
            print(f"  {c.get('region_code'):<3} {c.get('region_name')}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv=None):
    p = argparse.ArgumentParser(description="FastMoss unified market (API) module",
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("distribution", help="Fetch categoryDistribution (行业格局)")
    d.add_argument("--region", default="", help="Comma-separated region codes. Empty = global")
    d.add_argument("--time", choices=["28d", "month"], default="28d")
    d.add_argument("--pcid", type=int, default=None, help="Category id (default all)")
    d.add_argument("--out", required=True, help="Combined CSV path")
    d.add_argument("--raw-json", help="Also dump raw API responses here")
    d.add_argument("--session", default=DEFAULT_SESSION)

    b = sub.add_parser("base", help="Fetch GoodCategory/base (市场总览)")
    b.add_argument("--region", default="")
    b.add_argument("--action", default="1")
    b.add_argument("--pcid", type=int, default=None)
    b.add_argument("--out", required=True, help="Output JSON path")
    b.add_argument("--top-products-csv", help="Also write top_products CSV here")
    b.add_argument("--session", default=DEFAULT_SESSION)

    s = sub.add_parser("sales-chart", help="Fetch GoodCategory/salesChart (日销时序)")
    s.add_argument("--region", default="")
    s.add_argument("--action", default="1")
    s.add_argument("--pcid", type=int, default=None)
    s.add_argument("--out", required=True, help="Output CSV path")
    s.add_argument("--session", default=DEFAULT_SESSION)

    f = sub.add_parser("filter-info", help="Dump category/country vocabulary")
    f.add_argument("--out", help="Optional JSON output path")
    f.add_argument("--session", default=DEFAULT_SESSION)

    args = p.parse_args(argv)
    if args.cmd == "distribution":
        fetch_distribution(args.region, args.time, args.pcid, args.out, args.raw_json, args.session)
    elif args.cmd == "base":
        fetch_base(args.region, args.action, args.pcid, args.out, args.top_products_csv, args.session)
    elif args.cmd == "sales-chart":
        fetch_sales_chart(args.region, args.action, args.pcid, args.out, args.session)
    elif args.cmd == "filter-info":
        fetch_filter_info(args.out, args.session)


if __name__ == "__main__":
    main()
