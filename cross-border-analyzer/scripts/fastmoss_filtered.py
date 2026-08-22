#!/usr/bin/env python3
"""FastMoss 商品榜筛选抓取驱动（bsk 编排层）。

复用社区 fastmoss-rpa 的翻页 JS（vendor/fastmoss-rpa/sections.py），
补充社区工具不支持的能力：销量榜 URL、月榜 radio、新品榜日期范围。
商品表按实际表头动态映射列，兼容新品榜/销量榜表结构差异。
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
import time


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR = os.path.join(ROOT, "scripts", "vendor", "fastmoss-rpa")
sys.path.insert(0, VENDOR)

FIELDS = ["page", "rank", "product_name", "price", "listed_at", "country",
          "shop", "shop_total_sales", "category", "commission",
          "sales_period", "sales_growth", "gmv_period",
          "total_sales", "total_gmv", "image"]

# 新版 FastMoss 分页：真正的"下一页"按钮是 li.ant-pagination-next，
# 社区工具的 li[class*=next] 可能误点"跳页省略号"（before/after-jump-next）。
PAGE_NEXT_JS = """(() => {
  const sel = 'li.ant-pagination-next:not(.ant-pagination-disabled), ' +
              'li[title="下一页"]:not([class*=disabled])';
  const btn = document.querySelector(sel);
  if (!btn) return JSON.stringify({clicked:false});
  btn.click();
  return JSON.stringify({clicked:true});
})()"""

HEADER_MAP = {
    "排名": "rank", "商品": "product_name", "国家/地区": "country",
    "所属店铺": "shop", "商品分类": "category", "佣金比例": "commission",
    "销量": "sales_period", "三日销量": "sales_period", "月销量": "sales_period",
    "销量环比": "sales_growth",
    "销售额": "gmv_period", "三日销售额": "gmv_period", "月销售额": "gmv_period",
    "总销量": "total_sales", "总销售额": "total_gmv", "操作": None,
}

BSK = os.path.expanduser("~/.local/bin/bsk")


def bsk(args, session, timeout=60):
    r = subprocess.run([BSK] + args + ["--session", session],
                       capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def evaluate(js, session):
    code, out, err = bsk(["evaluate", js], session)
    if code != 0 or not out:
        raise RuntimeError(f"evaluate failed: {err or 'no output'}")
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"raw": out}


EXTRACT_JS = """(() => {
  const t = Array.from(document.querySelectorAll('table'))
    .find(x => x.innerText.includes('排名'));
  if (!t) return JSON.stringify({error: 'no table'});
  const trs = Array.from(t.querySelectorAll('tr'));
  const header = trs[0]
    ? Array.from(trs[0].querySelectorAll('th,td')).map(c => c.innerText.trim())
    : [];
  const rows = [];
  trs.forEach(r => {
    const tds = Array.from(r.querySelectorAll('td'));
    const cells = tds.map(c => c.innerText.trim());
    if (cells.length >= 6 && (cells[1] || '').includes('售价')) {
      const img = tds[1] ? tds[1].querySelector('img') : null;
      rows.push({cells, img: img ? img.src : ''});
    }
  });
  return JSON.stringify({header, rowCount: rows.length, rows});
})()"""


def click_label(text, session):
    js = ("(() => { const l = Array.from(document.querySelectorAll("
          "'label.ant-radio-button-wrapper')).find(x => "
          f"(x.innerText||'').trim() === '{text}'); "
          "if (!l) return JSON.stringify({clicked:false}); "
          "l.click(); return JSON.stringify({clicked:true}); })()")
    return evaluate(js, session)


def set_dates(start, end, session):
    for placeholder, val in (("开始日期", start), ("结束日期", end)):
        bsk(["fill", f'input[placeholder="{placeholder}"]', "--value", val], session)
    time.sleep(1)
    bsk(["press", "Escape"], session)
    time.sleep(2)


def verify_dates(start, end, session):
    vals = evaluate(
        "JSON.stringify(Array.from(document.querySelectorAll("
        "'input[placeholder*=日期]')).map(i=>i.value))",
        session,
    )
    return isinstance(vals, list) and vals[:2] == [start, end]


def parse_rows(header, items):
    names = [HEADER_MAP.get(h, "") for h in header]
    rows = []
    for item in items:
        cells = item["cells"] if isinstance(item, dict) else item
        img = (item.get("img") if isinstance(item, dict) else "") or ""
        if len(cells) < 6:
            continue
        row = {}
        for i, name in enumerate(names):
            if not name or i >= len(cells):
                continue
            if name == "product_name":
                text = cells[i].split("\n")
                row["product_name"] = (text[0] or "").strip()
                for line in text[1:]:
                    if "售价" in line:
                        row["price"] = line.split("：")[-1].split(":")[-1].strip()
                    elif "上架" in line:
                        row["listed_at"] = line.split("：")[-1].split(":")[-1].strip()
            elif name == "shop":
                parts = cells[i].split("\n")
                row["shop"] = (parts[0] or "").strip()
                if len(parts) > 1:
                    row["shop_total_sales"] = (
                        parts[1].replace("店铺销量：", "").replace("店铺销量:", "").strip())
            else:
                row[name] = cells[i].strip()
        if row.get("product_name"):
            row["image"] = img
            rows.append(row)
    return rows


def scrape(url, out, session, start=None, end=None, time_label=None,
           country="美国", category="时尚配件",
           pages=25, nav_sleep=5.0, page_sleep=3.5):
    code, out_s, err = bsk(["navigate", url, "--wait-until", "load", "--timeout", "45s"],
                           session)
    if code != 0:
        raise RuntimeError(f"navigate failed: {err}")
    time.sleep(nav_sleep)

    if start and end:
        set_dates(start, end, session)
        if not verify_dates(start, end, session):
            raise RuntimeError("日期范围设置未生效")
        time.sleep(2)
    if time_label:
        click_label(time_label, session)
        time.sleep(2)
    click_label(country, session)
    time.sleep(2)
    click_label(category, session)
    time.sleep(3)

    all_rows = {}
    for page in range(1, pages + 1):
        data = evaluate(EXTRACT_JS, session)
        if "error" in data:
            if page == 1:
                break
            time.sleep(3)
            data = evaluate(EXTRACT_JS, session)
            if "error" in data:
                break
        added = 0
        for row in parse_rows(data.get("header", []), data.get("rows", [])):
            row["page"] = page
            key = (row["product_name"], row["shop"])
            if key not in all_rows:
                all_rows[key] = row
                added += 1
        if added == 0 and page > 1:
            break
        nxt = evaluate(PAGE_NEXT_JS, session)
        if not nxt.get("clicked"):
            time.sleep(3)
            nxt = evaluate(PAGE_NEXT_JS, session)
        if not nxt.get("clicked"):
            break
        time.sleep(page_sleep)

    rows = list(all_rows.values())
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    import csv
    with open(out, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"OK {out}: {len(rows)} rows")


def main():
    ap = argparse.ArgumentParser(description="FastMoss 商品榜筛选抓取")
    ap.add_argument("--board", choices=["new", "sales"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--session", required=True)
    ap.add_argument("--pages", type=int, default=25)
    ap.add_argument("--page-sleep", type=float, default=3.5)
    ap.add_argument("--nav-sleep", type=float, default=5.0)
    ap.add_argument("--country", default="美国",
                    help="地区，按页面标签写，如 美国 / 英国 / 印尼（默认 美国）")
    ap.add_argument("--category", default="时尚配件",
                    help="品类，按页面标签写，如 时尚配件 / 美妆个护（默认 时尚配件）")
    ap.add_argument("--start", default=None,
                    help="新品榜开始日期 YYYY-MM-DD（默认近 30 天）")
    ap.add_argument("--end", default=None,
                    help="新品榜结束日期 YYYY-MM-DD（默认今天）")
    ap.add_argument("--time-label", default=None,
                    help="销量榜时间范围：月榜 / 周榜 / 日榜（默认 月榜）")
    args = ap.parse_args()

    if args.board == "new":
        url = "https://www.fastmoss.com/zh/e-commerce/newProducts"
        end = args.end or datetime.date.today().isoformat()
        start = args.start or (datetime.date.fromisoformat(end)
                               - datetime.timedelta(days=29)).isoformat()
        scrape(url, args.out, args.session,
               start=start, end=end,
               country=args.country, category=args.category,
               pages=args.pages, nav_sleep=args.nav_sleep,
               page_sleep=args.page_sleep)
    else:
        url = "https://www.fastmoss.com/zh/e-commerce/saleslist"
        scrape(url, args.out, args.session,
               time_label=args.time_label or "月榜",
               country=args.country, category=args.category,
               pages=args.pages, nav_sleep=args.nav_sleep,
               page_sleep=args.page_sleep)


if __name__ == "__main__":
    main()
