---
name: fastmoss-rpa
description: "Unified FastMoss (fastmoss.com) TikTok Shop RPA . Covers all 7 boards: PRODUCT rankings (新品/销量/热推/视频商品榜, with country/category/shop-type filters + single-shop cadence), CREATOR rankings (涨粉/带货/蓝V/热门/黑马), SHOP rankings (销量/热推), ADS trends (标签/关键词/品类), CREATIVE materials (视频/音乐/标签), LIVESTREAM rankings (TT直播/直播爆品/直播带货达人), and the MARKET category-distribution API (行业格局/市场总览/日销时序). Use whenever the user wants to scrape, filter, analyze, or pull any FastMoss TikTok Shop data. Drives the user's real logged-in browser via BrowserSkill (bsk). Self-contained — includes environment notes and 7 Markdown report templates."
---

# fastmoss-rpa (unified)

**One skill, seven boards.** This consolidates the previous seven sister skills
(`fastmoss-products`, `fastmoss-creators`, `fastmoss-shops`, `fastmoss-ads`,
`fastmoss-creatives`, `fastmoss-livestreams`, `fastmoss-market`) into a single
entry point. The scraping logic lives in one generic engine (`scripts/core.py`);
all board differences are data in `scripts/sections.py`. The old
`.claude/skills/fastmoss-*` directories are **kept as backup** and are not deleted.

## Architecture

```
fastmoss_rpa.py            # single CLI: scrape / filter / analyze / market
  ├─ core.py           # generic paginating engine (fixed + dynamic parse modes)
  ├─ market_api.py     # FastMoss JSON-API fetchers (page-context fetch)
  ├─ analyze.py        # 7 report engines, dispatched by --section
  ├─ sections.py       # CONFIG: URLs, parsers, fields, filter dims (no logic to rewrite)
  ├─ bridge_browserskill.py  # transport: call / evaluate / session_stop
  └─ references/
        ├─ api_notes.md      # FastMoss API contract (market)
        └─ reports/<section>.md  # 7 Markdown report templates
```

## Prerequisites

- **BrowserSkill (`bsk`)** installed and connected; the BrowserSkill extension
  is installed in Chrome/Edge and the user is **logged into fastmoss.com**.
  Verify with `bsk status` → `browsers connected: N` (N ≥ 1).
- No local HTTP daemon — bsk drives the real browser and reuses the login
  session (cookies + origin), which is why the market API calls work.

Full environment/shell quirks are in `references/environment.md`.

## Critical gotchas (each cost real time on first run)

1. **Never click via `@e` snapshot refs** — they go stale after every navigation.
   All bundled clicks use text-label `evaluate` JS.
2. **Bash heredoc + JS regex breaks** (backslash layer eaten). Prefer `.split('\n')`.
3. **SPA hydration lag** — wait ≥5 s after `navigate`, ≥3.5 s between pages. Too
   fast → 0 rows. (`--nav-sleep` / `--page-sleep` tune this.)
4. **Python encoding on Windows** — always read produced CSVs with
   `encoding='utf-8-sig'`.
5. **Empty filler top row** on page 1 — parsers drop rows whose key field is empty.

## Boards at a glance

| Board (`--section`) | Mode | Filter dims | Ranking keys (`--ranking`) |
|---|---|---|---|
| `products` | fixed | country, category, shop_type | *(none — single page)* |
| `creators` | dynamic | country, time | fans, commerceTop, blue-v, popular, potentialTop |
| `shops` | dynamic | country | sales, hot |
| `ads` | dynamic | country | tag, keyword, category |
| `creatives` | dynamic | country | video, song, hashtag |
| `livestreams` | dynamic | country | tiktok, hotProduct, liveCommerce |
| `market` | API | region (code) + time | *(API endpoints, see `market`)* |

### Country label vocabulary (16 markets)

Used for `--country` filter clicks (Chinese labels FastMoss displays):

```
美国 印度尼西亚 英国 越南 泰国 马来西亚 菲律宾 西班牙
墨西哥 德国 法国 意大利 巴西 日本 新加坡 沙特
```

`market` uses **region codes** instead: `US ID GB VN TH MY PH ES MX DE FR IT BR JP SG SA`
(see `references/api_notes.md`).

## Commands

All commands run from the skill's `scripts/` directory (or with that dir on
`PYTHONPATH`). Replace `<out>` with any path; parent dirs are created.

### 1) scrape — one ranking, no filter

```bash
# Products (fixed schema, no --ranking needed)
python fastmoss_rpa.py scrape --section products --pages 5 --out <out>/products.csv

# Dynamic boards need --ranking
python fastmoss_rpa.py scrape --section creators   --ranking fans          --pages 5 --out <out>/fans.csv
python fastmoss_rpa.py scrape --section shops      --ranking sales         --pages 5 --out <out>/sales.csv
python fastmoss_rpa.py scrape --section ads        --ranking keyword       --pages 5 --out <out>/keywords.csv
python fastmoss_rpa.py scrape --section creatives  --ranking video         --pages 5 --out <out>/videos.csv
python fastmoss_rpa.py scrape --section livestreams--ranking tiktok         --pages 5 --out <out>/tiktok.csv

# Custom URL (overrides --ranking)
python fastmoss_rpa.py scrape --section creators --url "https://www.fastmoss.com/zh/influencer/tiktok/fans" --out <out>/x.csv
```

### 2) filter — with country / category / time filter

Products supports one of `country` / `category` / `shop_type` per run and writes
a per-label CSV + a combined CSV:

```bash
python fastmoss_rpa.py filter --section products --category "美妆个护,女装与女士内衣" --pages 3 --out <out>/by_category.csv
python fastmoss_rpa.py filter --section products --country 美国,印度尼西亚 --pages 3 --out <out>/by_country.csv
python fastmoss_rpa.py filter --section products --shop-type 跨境店 --pages 3 --out <out>/by_shop_type.csv
```

Dynamic boards support `--country` (and creators also `--time`, e.g. `周榜`):

```bash
python fastmoss_rpa.py filter --section creators --ranking fans --country 美国,印度尼西亚,泰国,马来西亚 --pages 3 --out <out>/fans_by_country.csv
python fastmoss_rpa.py filter --section creators --ranking commerceTop --country 美国 --time 周榜 --pages 3 --out <out>/commerce_us_weekly.csv
python fastmoss_rpa.py filter --section shops    --ranking sales --country 美国,泰国 --pages 3 --out <out>/sales_by_country.csv
python fastmoss_rpa.py filter --section ads      --ranking keyword --country 美国,印度尼西亚 --pages 3 --out <out>/keywords_by_country.csv
```

### 3) analyze — multi-dimensional Markdown report

```bash
# Products (top50 + optional by-country / by-category / per-shop)
python fastmoss_rpa.py analyze products \
    --top50 <out>/top50.csv --by-country <out>/by_country.csv \
    --by-category <out>/by_category.csv --shop <out>/shop_X.csv \
    --out-md <report>/products_report.md

# Creators / shops / ads / creatives / livestreams
python fastmoss_rpa.py analyze creators --fans <out>/fans.csv --commerce <out>/commerce.csv \
    --blue-v <out>/blue-v.csv --popular <out>/popular.csv --horse <out>/horse.csv --out-md <report>/creators_report.md
python fastmoss_rpa.py analyze shops --sales <out>/sales.csv --hot <out>/hot.csv --out-md <report>/shops_report.md
python fastmoss_rpa.py analyze ads --tag <out>/tags.csv --keyword <out>/keywords.csv --category <out>/categories.csv --out-md <report>/ads_report.md
python fastmoss_rpa.py analyze creatives --video <out>/videos.csv --song <out>/songs.csv --hashtag <out>/hashtags.csv --out-md <report>/creatives_report.md
python fastmoss_rpa.py analyze livestreams --tiktok <out>/tiktok.csv --hot-product <out>/hot_product.csv --live-commerce <out>/live_commerce.csv --out-md <report>/livestreams_report.md

# Combine a multi-filter CSV via --filtered
python fastmoss_rpa.py analyze creators --filtered <out>/fans_by_country.csv --out-md <report>/creators_report.md
```

### 4) market — FastMoss category-distribution API

```bash
# Industry pattern (categoryDistribution) — multi-region comparison
python fastmoss_rpa.py market distribution --region US,ID,TH,MY --time month --out <out>/categories_by_region.csv
python fastmoss_rpa.py market distribution --region US --pcid 14 --time month --out <out>/us_beauty.csv

# Market overview (GoodCategory/base) + top products
python fastmoss_rpa.py market base --region US --out <out>/us_market_base.json --top-products-csv <out>/us_top_products.csv

# Daily sales time-series (GoodCategory/salesChart)
python fastmoss_rpa.py market sales-chart --region US --out <out>/us_sales_chart.csv

# Dump category/country vocabulary (pcid codes etc.)
python fastmoss_rpa.py market filter-info --out <out>/filter_info.json

# Then render the market report
python fastmoss_rpa.py analyze market --distribution <out>/categories_by_region.csv --out-md <report>/market_report.md
```

## CSV schemas

- **products**: `page, rank, product_name, price, listed_at, country, shop, shop_total_sales, category, commission, sales_period, gmv_period, total_sales, total_gmv`
- **creators**: `page, ranking, rank, creator_name, creator_id, creator_category, country` + dynamic header columns
- **shops**: `page, ranking, rank, shop_name, shop_legal_name, shop_category, shop_rating` + dynamic header columns
- **ads / creatives / livestreams**: `page, ranking, rank, entity_name` + dynamic header columns
- **filtered**: adds `filter` (products) or `filter_country` (+ `filter_time` for creators) as the leading column(s).
- **market**: see `references/api_notes.md` for API field names.

The 7 report templates in `references/reports/` are auto-filled by `analyze.py`
— do not rename their `{placeholder}` tokens.

## Migration note

The previous 7 skills under `.claude/skills/fastmoss-*/` are preserved as a
backup. This unified skill is the maintained entry point; once you've validated
it against your workflows you may delete the old directories. Behavior is
intended to be byte-for-byte identical for the CSV outputs.
