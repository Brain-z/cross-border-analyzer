"""Section registry for the unified FastMoss skill.

Every FastMoss board is the same paginating scraper with a different
configuration: ranking URLs, the row parser, the output fields, and the
supported filter dimensions. This module collects all 7 boards' configs in
one place. The parsers below are copied verbatim from the original
per-board scripts (fastmoss-products / fastmoss-creators / ... ) — do NOT
rewrite them; correctness of the extracted data depends on the exact logic.

Transport (call/evaluate/session_stop) comes from bridge_browserskill.
"""

import re

# ---------------------------------------------------------------------------
# Shared JS fragments (identical across boards)
# ---------------------------------------------------------------------------

# Next-page click — same selector in every board.
# 注意：不要用 `li[class*=next]`，会命中分页省略号导致翻页中断；用 ant 分页的 next 类。
NEXT_PAGE_JS = """
(() => {
  const sel = 'li[title="\\u4e0b\\u4e00\\u9875"], li.ant-pagination-next:not(.ant-pagination-disabled)';
  const btn = document.querySelector(sel);
  if (!btn) return JSON.stringify({clicked: false});
  btn.click();
  return JSON.stringify({clicked: true});
})()
"""

# Dynamic-table extractor (reads thead headers + tbody rows, with cell-text
# fallback for Ant Design sticky-header clones). Used by shops/ads/creatives/
# livestreams.
DYNAMIC_EXTRACT_JS = """
(() => {
  const tables = document.querySelectorAll('table');
  if (!tables.length) return JSON.stringify({error: 'no table', url: location.href});
  const readCell = (el) => {
    let txt = (el.innerText || '').trim();
    if (txt) return txt;
    txt = (el.textContent || '').trim();
    if (txt) return txt;
    return (el.getAttribute('title') || '').trim();
  };
  let headers = [];
  let rows = [];
  tables.forEach(t => {
    if (!headers.length) {
      const hs = Array.from(t.querySelectorAll('thead th')).map(readCell).filter(x => x);
      if (hs.length) headers = hs;
    }
    if (!rows.length) {
      const rs = [];
      t.querySelectorAll('tbody tr').forEach(r => {
        const cells = Array.from(r.querySelectorAll('td')).map(c => c.innerText.trim());
        if (cells.length >= 3) rs.push(cells);
      });
      if (rs.length) rows = rs;
    }
  });
  return JSON.stringify({headers, rows, title: document.title});
})()
"""

# Creators' own (simpler) dynamic extractor — kept verbatim.
CREATORS_EXTRACT_JS = """
(() => {
  const tables = document.querySelectorAll('table');
  if (!tables.length) return JSON.stringify({error: 'no table', url: location.href});
  const table = tables[tables.length - 1];
  const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.innerText.trim());
  const rows = [];
  table.querySelectorAll('tbody tr').forEach(r => {
    const cells = Array.from(r.querySelectorAll('td')).map(c => c.innerText.trim());
    if (cells.length >= 4) rows.push(cells);
  });
  return JSON.stringify({headers, rows, title: document.title});
})()
"""

# Products' fixed-schema extractor — reads raw tr/td (no headers).
PRODUCTS_EXTRACT_JS = """
(() => {
  const tables = document.querySelectorAll('table');
  if (!tables.length) return JSON.stringify({error: 'no table', url: location.href});
  const table = tables[tables.length - 1];
  const out = [];
  table.querySelectorAll('tr').forEach(r => {
    const cells = Array.from(r.querySelectorAll('td'));
    if (cells.length < 5) return;
    out.push(cells.map(c => c.innerText.trim()));
  });
  return JSON.stringify({rowCount: out.length, rows: out, title: document.title});
})()
"""

# Products' filter click templates (country / category / shop_type).
PRODUCTS_CLICK_COUNTRY_JS = """
((label) => {
  const radios = Array.from(document.querySelectorAll('input[type="radio"]'));
  const t = radios.find(r => {
    const parent = r.closest('label') || r.parentElement;
    return parent && parent.innerText.includes(label);
  });
  if (!t) return JSON.stringify({clicked: false, count: radios.length});
  t.click();
  return JSON.stringify({clicked: true, value: t.value, checked: t.checked});
})(%s)
"""

PRODUCTS_CLICK_CATEGORY_JS = """
((label) => {
  const expand = Array.from(document.querySelectorAll('span, button, a'))
    .find(el => el.innerText && el.innerText.trim() === '展开');
  if (expand) { try { expand.click(); } catch(e) {} }
  const t = Array.from(document.querySelectorAll('span, a, button, div'))
    .find(el => el.innerText && el.innerText.trim() === label && el.offsetParent !== null);
  if (!t) return JSON.stringify({clicked: false, expanded: !!expand});
  t.click();
  return JSON.stringify({clicked: true, expanded: !!expand});
})(%s)
"""

PRODUCTS_CLICK_SHOP_TYPE_JS = """
((label) => {
  const radios = Array.from(document.querySelectorAll('input[type="radio"]'));
  const t = radios.find(r => {
    const parent = r.closest('label') || r.parentElement;
    return parent && parent.innerText.includes(label);
  });
  if (!t) return JSON.stringify({clicked: false});
  t.click();
  return JSON.stringify({clicked: true, value: t.value});
})(%s)
"""

# Country radio click (used by creators/shops/ads/creatives/livestreams).
CLICK_COUNTRY_JS = """
((label) => {
  const radios = Array.from(document.querySelectorAll('input[type="radio"]'));
  const t = radios.find(r => {
    const parent = r.closest('label') || r.parentElement;
    return parent && parent.innerText.includes(label);
  });
  if (!t) return JSON.stringify({clicked: false, reason: 'country not found'});
  t.click();
  return JSON.stringify({clicked: true, value: t.value});
})(%s)
"""

# Time-window radio click (creators only).
CLICK_TIME_JS = """
((label) => {
  const radios = Array.from(document.querySelectorAll('input[type="radio"]'));
  const t = radios.find(r => {
    const parent = r.closest('label') || r.parentElement;
    return parent && parent.innerText.trim() === label;
  });
  if (!t) return JSON.stringify({clicked: false, reason: 'time label not found'});
  t.click();
  return JSON.stringify({clicked: true, value: t.value});
})(%s)
"""


# ---------------------------------------------------------------------------
# Helpers (identical across boards)
# ---------------------------------------------------------------------------

def sanitize_header(h):
    if not h:
        return ""
    return h.replace("\n", " ").replace("\r", " ").strip()


def parse_entity_name(cell, limit=120):
    if not cell:
        return ""
    first_line = cell.split("\n")[0].strip()
    return first_line[:limit]


# ---------------------------------------------------------------------------
# Per-board parsers (verbatim logic)
# ---------------------------------------------------------------------------

def products_parse_row(cells):
    """Parse a product table row (fixed schema)."""
    if len(cells) < 10:
        return None
    product_raw = cells[1].split("\n")
    product_name = product_raw[0] if product_raw else ""
    if not product_name.strip():
        return None
    price = ""
    listed_at = ""
    for line in product_raw[1:]:
        if "售价" in line:
            price = line.split("：")[-1].split(":")[-1].strip()
        elif "上架" in line:
            listed_at = line.split("：")[-1].split(":")[-1].strip()
    shop_raw = cells[3].split("\n")
    shop = shop_raw[0].strip() if shop_raw else ""
    shop_total_sales = ""
    if len(shop_raw) > 1:
        shop_total_sales = shop_raw[1].replace("店铺销量：", "").replace("店铺销量:", "").strip()
    return {
        "rank": cells[0].strip(),
        "product_name": product_name.strip(),
        "price": price,
        "listed_at": listed_at,
        "country": cells[2].strip(),
        "shop": shop,
        "shop_total_sales": shop_total_sales,
        "category": cells[4].strip(),
        "commission": cells[5].strip(),
        "sales_period": cells[6].strip() if len(cells) > 6 else "",
        "gmv_period": cells[7].strip() if len(cells) > 7 else "",
        "total_sales": cells[8].strip() if len(cells) > 8 else "",
        "total_gmv": cells[9].strip() if len(cells) > 9 else "",
    }


def creators_parse_row(headers, cells):
    if not any(c.strip() for c in cells):
        return None
    row = {}
    for i, h in enumerate(headers):
        if i >= len(cells):
            break
        if h in ("操作", ""):
            continue
        row[sanitize_header(h)] = cells[i]
    rank = cells[0].strip() if cells else ""
    row["rank"] = rank
    creator_field = row.get("达人") or row.get("达人信息") or ""
    parts = [p.strip() for p in creator_field.split("\n") if p.strip()]
    row["creator_name"] = parts[0] if parts else ""
    row["creator_id"] = ""
    row["creator_category"] = ""
    for p in parts[1:]:
        if p.startswith("ID"):
            row["creator_id"] = p.replace("ID：", "").replace("ID:", "").strip()
        elif not row["creator_category"] and p not in ("男", "女") and "%" not in p and "-" not in p[:3] and not p[0].isdigit():
            row["creator_category"] = p
    row["country"] = row.get("国家/地区", "").strip()
    return row


def parse_shop_cell(cell):
    parts = [p.strip() for p in cell.split("\n") if p.strip()]
    shop_name = ""
    legal = ""
    category = ""
    rating = ""
    for p in parts:
        if p == "品牌":
            continue
        if re.fullmatch(r"\d+\.\d+", p):
            rating = p
        elif not shop_name:
            shop_name = p
        elif not legal and (p.isupper() or "PT" in p or "INC" in p or "CO" in p or "LLC" in p or "SDN" in p or "LTD" in p or "TRADING" in p):
            legal = p
        elif not category and len(p) <= 12 and p not in ("男", "女"):
            category = p
    return shop_name, legal, category, rating


def shops_parse_row(headers, cells):
    if not any(c.strip() for c in cells):
        return None
    row = {}
    for i, h in enumerate(headers):
        if i >= len(cells):
            break
        if h in ("操作", ""):
            continue
        row[sanitize_header(h)] = cells[i]
    rank = cells[0].strip() if cells else ""
    row["rank"] = rank
    shop_field = row.get("店铺", "")
    shop_name, legal, category, rating = parse_shop_cell(shop_field)
    row["shop_name"] = shop_name
    row["shop_legal_name"] = legal
    row["shop_category"] = category
    row["shop_rating"] = rating
    return row


def ads_parse_row(headers, cells, entity_header):
    if not any(c.strip() for c in cells):
        return None
    row = {}
    for i, h in enumerate(headers):
        if i >= len(cells):
            break
        if h in ("操作", ""):
            continue
        row[sanitize_header(h)] = cells[i]
    rank = cells[0].strip() if cells else ""
    row["rank"] = rank
    entity_cell = row.get(entity_header, "")
    row["entity_name"] = parse_entity_name(entity_cell, 120)
    return row


def creatives_parse_row(headers, cells, entity_header):
    if not any(c.strip() for c in cells):
        return None
    row = {}
    for i, h in enumerate(headers):
        if i >= len(cells):
            break
        if h in ("操作", ""):
            continue
        row[sanitize_header(h)] = cells[i]
    rank = cells[0].strip() if cells else ""
    row["rank"] = rank
    entity_cell = row.get(entity_header, "")
    row["entity_name"] = parse_entity_name(entity_cell, 120)
    return row


def livestreams_parse_row(headers, cells, entity_header):
    if not any(c.strip() for c in cells):
        return None
    row = {}
    for i, h in enumerate(headers):
        if i >= len(cells):
            break
        if h in ("操作", ""):
            continue
        row[sanitize_header(h)] = cells[i]
    rank = cells[0].strip() if cells else ""
    row["rank"] = rank
    entity_cell = row.get(entity_header, "")
    row["entity_name"] = parse_entity_name(entity_cell, 80)
    return row


# ---------------------------------------------------------------------------
# Section registry
# ---------------------------------------------------------------------------

PRODUCTS_FIELDS = ["page", "rank", "product_name", "price", "listed_at", "country",
                   "shop", "shop_total_sales", "category", "commission",
                   "sales_period", "gmv_period", "total_sales", "total_gmv"]

CREATORS_FIELDS = ["page", "ranking", "rank", "creator_name", "creator_id",
                   "creator_category", "country"]

SHOPS_FIELDS = ["page", "ranking", "rank", "shop_name", "shop_legal_name",
                "shop_category", "shop_rating"]

ENTITY_FIELDS = ["page", "ranking", "rank", "entity_name"]

SECTIONS = {
    "products": {
        "mode": "fixed",
        "parse_kind": "fixed",
        "url": "https://www.fastmoss.com/zh/e-commerce/newProducts",
        "extract_js": PRODUCTS_EXTRACT_JS,
        "next_page_js": NEXT_PAGE_JS,
        "parse_row": products_parse_row,
        "base_fields": PRODUCTS_FIELDS,
        "nav_sleep": 5.0,
        "group_title": "fastmoss-products",
        "filter_dims": ["country", "category", "shop_type"],
        "click_templates": {
            "country": PRODUCTS_CLICK_COUNTRY_JS,
            "category": PRODUCTS_CLICK_CATEGORY_JS,
            "shop_type": PRODUCTS_CLICK_SHOP_TYPE_JS,
        },
    },
    "creators": {
        "mode": "dynamic",
        "parse_kind": "headers",
        "rankings": {
            "fans": "https://www.fastmoss.com/zh/influencer/tiktok/fans",
            "commerceTop": "https://www.fastmoss.com/zh/influencer/tiktok/commerceTop",
            "blue-v": "https://www.fastmoss.com/zh/influencer/tiktok/blue-v",
            "popular": "https://www.fastmoss.com/zh/influencer/tiktok/popular",
            "potentialTop": "https://www.fastmoss.com/zh/influencer/tiktok/potentialTop",
        },
        "extract_js": CREATORS_EXTRACT_JS,
        "next_page_js": NEXT_PAGE_JS,
        "parse_row": creators_parse_row,
        "base_fields": CREATORS_FIELDS,
        "nav_sleep": 6.0,
        "group_title": "fastmoss-creators",
        "filter_dims": ["country", "time"],
        "click_templates": {
            "country": CLICK_COUNTRY_JS,
            "time": CLICK_TIME_JS,
        },
    },
    "shops": {
        "mode": "dynamic",
        "parse_kind": "headers",
        "rankings": {
            "sales": "https://www.fastmoss.com/zh/shop-marketing/tiktok",
            "hot": "https://www.fastmoss.com/zh/shop-marketing/hotTiktok",
        },
        "extract_js": DYNAMIC_EXTRACT_JS,
        "next_page_js": NEXT_PAGE_JS,
        "parse_row": shops_parse_row,
        "base_fields": SHOPS_FIELDS,
        "nav_sleep": 6.0,
        "group_title": "fastmoss-shops",
        "filter_dims": ["country"],
        "click_templates": {"country": CLICK_COUNTRY_JS},
    },
    "ads": {
        "mode": "dynamic",
        "parse_kind": "headers_entity",
        "rankings": {
            "tag": "https://www.fastmoss.com/zh/creativecenter/insightTag",
            "keyword": "https://www.fastmoss.com/zh/creativecenter/keyword-trends",
            "category": "https://www.fastmoss.com/zh/creativecenter/product-category-trends",
        },
        "entity_headers": {
            "tag": "标签",
            "keyword": "关键词",
            "category": "热门品类",
        },
        "extract_js": DYNAMIC_EXTRACT_JS,
        "next_page_js": NEXT_PAGE_JS,
        "parse_row": ads_parse_row,
        "base_fields": ENTITY_FIELDS,
        "nav_sleep": 6.0,
        "group_title": "fastmoss-ads",
        "filter_dims": ["country"],
        "click_templates": {"country": CLICK_COUNTRY_JS},
    },
    "creatives": {
        "mode": "dynamic",
        "parse_kind": "headers_entity",
        "rankings": {
            "video": "https://www.fastmoss.com/zh/media-source/video",
            "song": "https://www.fastmoss.com/zh/media-source/song",
            "hashtag": "https://www.fastmoss.com/zh/media-source/hashtag",
        },
        "entity_headers": {
            "video": "视频内容",
            "song": "音乐",
            "hashtag": "标签",
        },
        "extract_js": DYNAMIC_EXTRACT_JS,
        "next_page_js": NEXT_PAGE_JS,
        "parse_row": creatives_parse_row,
        "base_fields": ENTITY_FIELDS,
        "nav_sleep": 6.0,
        "group_title": "fastmoss-creatives",
        "filter_dims": ["country"],
        "click_templates": {"country": CLICK_COUNTRY_JS},
    },
    "livestreams": {
        "mode": "dynamic",
        "parse_kind": "headers_entity",
        "rankings": {
            "tiktok": "https://www.fastmoss.com/zh/live/tiktok",
            "hotProduct": "https://www.fastmoss.com/zh/live/hotProduct",
            "liveCommerce": "https://www.fastmoss.com/zh/live/liveCommerce",
        },
        "entity_headers": {
            "tiktok": "直播间",
            "hotProduct": "商品",
            "liveCommerce": "达人",
        },
        "extract_js": DYNAMIC_EXTRACT_JS,
        "next_page_js": NEXT_PAGE_JS,
        "parse_row": livestreams_parse_row,
        "base_fields": ENTITY_FIELDS,
        "nav_sleep": 6.0,
        "group_title": "fastmoss-livestreams",
        "filter_dims": ["country"],
        "click_templates": {"country": CLICK_COUNTRY_JS},
    },
}


def get_entity_header(section, ranking_key):
    return SECTIONS[section].get("entity_headers", {}).get(ranking_key, "")
