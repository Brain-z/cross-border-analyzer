# FastMoss Market API Contract

Reverse-engineered from `https://www.fastmoss.com/zh/market/market-category` and `/market-analyze` (observed via network capture during skill build, 2026-07-03).

All endpoints are JSON, GET method, served from `https://www.fastmoss.com`. Auth = session cookies (sent automatically by `fetch(..., {credentials: 'include'})` from page context).

## Anti-cache params

Every request includes `_time=<unix-seconds>&cnonce=<random-8-digit>`. They appear to be required (or at least expected) — they don't affect the response, but omitting them may return cached data. The bundled `fetch_json()` in `scripts/common.py` adds them automatically.

## Vocabularies

### Region codes (16 markets)

| Code | 中文 |
|---|---|
| US | 美国 |
| ID | 印度尼西亚 |
| GB | 英国 |
| VN | 越南 |
| TH | 泰国 |
| MY | 马来西亚 |
| PH | 菲律宾 |
| ES | 西班牙 |
| MX | 墨西哥 |
| DE | 德国 |
| FR | 法国 |
| IT | 意大利 |
| BR | 巴西 |
| JP | 日本 |
| SG | 新加坡 |
| SA | 沙特 |

Empty region param = global aggregate. **Note**: pass an empty string in the bundled script's `--region ""` to get the global view.

### Category codes (pcid)

27 categories, ranked by traffic. Top 10:

| pcid | 中文 | rank |
|---|---|---|
| 14 | 美妆个护 | 1 |
| 2 | 女装与女士内衣 | 6 |
| 25 | 保健 | 9 |
| 8 | 时尚配件 | 11 |
| 9 | 运动与户外 | 16 |
| 16 | 手机与数码 | 26 |
| 10 | 居家日用 | 31 |
| 24 | 食品饮料 | 36 |
| 23 | 汽车与摩托车 | 41 |
| 3 | 男装与男士内衣 | 44 |

Run `python scripts/fetch_filter_info.py` to dump the current full mapping.

## Endpoints

### 1. `GET /api/analysis/V2/categoryDistribution` — 行业格局 scatter data

**Page**: `market-category` 行业格局 tab.

**Query params**:
- `region` (optional, default = global if omitted; explicit `US`/`ID`/etc)
- `date_value` (optional; omit for last-28-days mode, send `YYYY-MM` for month mode)
- `pcid` (optional; omit for all categories, send a single category code)
- `is_mock=0` (always sent)

**Response shape**:
```json
{
  "code": 200,
  "data": {
    "dots": [
      {
        "region": "US",
        "region_name": "美国",
        "category_id": 3,
        "category_name": "男装与男士内衣",
        "category_sale_amount": 111095000,
        "category_sale_amount_show": "$1.1亿+",
        "category_sale_amount_mom": 2400,
        "category_sale_amount_mom_rate": "24%",
        "category_sale_amount_mom_rate_show": "24%",
        "cur_sale_amount": 111094835.07,
        "cur_sale_amount_show": "$1.11亿",
        "last_sale_amount": 89442848.01,
        "last_sale_amount_show": "$8944.28万"
      }
    ]
  }
}
```

`category_sale_amount_mom_rate` is a string like `"24%"`. Parse with `.rstrip('%')` for sorting.

### 2. `GET /api/analysis/GoodCategory/base` — market overview

**Page**: `market-analyze`.

**Query params**:
- `region` (optional)
- `action` (required; default `1` = daily granularity. Other values not yet enumerated.)
- `pcid` (optional)

**Response shape** (heavily abbreviated):
```json
{
  "code": 200,
  "data": {
    "dt": "2026-07-02",
    "region": "US",
    "category_id": -100,
    "category_name": "",
    "category_sold_count": 2950000,
    "category_sold_count_show": "295万+",
    "category_sold_count_mom_rate": "-11.96%",
    "category_sold_count_yoy_rate": "2.9%",
    "category_sale_amount": 91007316.11,
    "category_sale_amount_mom_rate": "0%",
    "category_sale_amount_yoy_rate": "7.63%",
    "product_count": "17867509",
    "sales_product_count": "414902",
    "sales_author_count": 251510,
    "sales_video_count": "169605",
    "sales_live_count": "14267",
    "top_products_statistics_info": {
      "average_affiliate_count": 325,
      "average_live_count": 102,
      "average_video_count": 305,
      "period": "2026-07-02"
    },
    "top_products": [
      {
        "product_id": "1729508370969629931",
        "title": "[NEW] [medicube] PDRN Pink Collagen ...",
        "sold_count": 8887,
        "sale_amount": 223063.7,
        "total_sold_count": 852667,
        "total_sale_amount": 19434177.83,
        "launch_time": "2026-03-18 13:11:24",
        "sold_count_inc_rate": "-16.22%",
        "aweme_count": 171,
        "live_count": 205,
        "author_count": 290
      }
    ]
  }
}
```

### 3. `GET /api/analysis/GoodCategory/salesChart` — daily time-series

**Page**: `market-analyze`.

**Query params**: same as `base`.

**Response shape**:
```json
{
  "code": 200,
  "data": {
    "list": [
      {
        "dt": "2026-06-02",
        "data_value": "2026-06-02",
        "category_sold_count": 2372600,
        "category_sold_count_show": "237.26万",
        "inc_product_count": 177104,
        "inc_product_count_show": "17.71万",
        "sales_product_count": 354105,
        "sales_product_count_show": "35.41万",
        "sales_author_count": 265615,
        "sales_video_count": 150804,
        "sales_live_count": 13295
      }
    ]
  }
}
```

### 4. `GET /api/analysis/GoodCategory/priceDistribution` — price-band distribution

**Page**: `market-analyze` 价格带趋势 tab.

**Query params**: same as `base`.

**Response shape**: not yet documented in detail. The bundled scripts don't call this — extend when needed.

### 5. `GET /api/analysis/GoodCategory/filterInfo` — vocabularies

**Page**: both market pages call this once on load.

**Query params**: none (just `_time` + `cnonce`).

**Response shape**:
```json
{
  "code": 200,
  "data": {
    "category": [
      {"c_code": 14, "c_name": "美妆个护", "rank": 1}
    ],
    "country": [
      {"region_code": "US", "region": "US", "region_name": "美国"}
    ]
  }
}
```

## Gotchas

1. **`region=Global` doesn't work** — for the global aggregate, omit the `region` param entirely. The bundled `fetch_distribution.py` handles this when `--region` is empty.
2. **`date_value=YYYY-MM`** uses the most recent **completed** month. `fetch_distribution.py:most_recent_completed_month()` handles month wrap.
3. **`action=1`** for `base`/`salesChart` is the only observed value. Likely enum: 1=daily, 2=weekly(?), 3=monthly(?). Test before assuming.
4. **Responses can be large** — `salesChart` returns ~28 daily rows (manageable). `base.top_products` can have 50+ items. `categoryDistribution` returns up to ~27 categories × 1 region per call.
5. **No pagination needed** — all data returned in one response.
6. **4xx on auth failure** — if the user is logged out, the API returns a 401/403. Always do `bsk status` + verify login before debugging deeper.
