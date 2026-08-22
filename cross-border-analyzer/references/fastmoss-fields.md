# FastMoss 字段与提取说明

## 商品榜常见字段（抓取后按实际列名核对）

| 常见列 | 含义 | 清洗后的规范列 |
|---|---|---|
| 排名 | 榜单名次 | rank |
| 商品名 / 商品标题 | 商品名称 | name |
| 价格 | 售价（美元） | price |
| 周期销量 | 当前榜单周期的销量 | sales7 |
| 周期 GMV | 当前榜单周期的销售额 | gmv7 |
| 总销量 / 累计销量 | 历史总销量 | sales_total |
| 总 GMV | 历史总销售额 | gmv_total |
| 佣金率 | 达人佣金比例 | commission |
| 上架时间 / 上架天数 | 商品生命周期 | listed_days（日期自动折算天数） |
| 店铺 | 所属店铺 | shop |
| 品类 | 类目 | category |
| 评分 / 店铺评分 | 店铺或商品评分 | rating |
| 评论数 | 评论数量 | reviews |
| 商品图 | 商品缩略图地址（抓取时取自商品单元格首个 img） | image |

## 提取 JS（bsk evaluate 用）

FastMoss 页面结构会变，优先读表头做字段自适应；商品单元格里有缩略图时，
把首个 `img.src` 一并取回（对应 `image` 列）：

```js
(() => {
  const tables = Array.from(document.querySelectorAll('table'));
  if (!tables.length) return { error: 'no table found' };
  const rows = [];
  for (const t of tables) {
    for (const tr of t.querySelectorAll('tr')) {
      const cells = Array.from(tr.querySelectorAll('th,td')).map(c => c.innerText.trim());
      const tds = Array.from(tr.querySelectorAll('td'));
      const img = tds[1] ? tds[1].querySelector('img') : null;
      if (cells.length) rows.push({cells, img: img ? img.src : ''});
    }
  }
  return { rows };
})()
```

榜单抓取直接走 `scripts/fastmoss_filtered.py`（商品榜）或
`scripts/vendor/fastmoss-rpa/fastmoss_rpa.py`（其余模块），无需手工转 CSV；
手工导出的文件放到 `data/import/` 后由 `scripts/normalize.py` 清洗。

## 更稳的替代：页面 JSON 接口

打开开发者工具 Network，过滤 `api` / `json`，榜单数据往往来自同源 JSON 接口。
在 `bsk evaluate` 里直接 `fetch()` 该接口可免翻页（参考
`scripts/vendor/fastmoss-rpa/market_api.py`），返回 JSON 用 Python 标准库
`json` / `csv` 落盘为 UTF-8 BOM CSV。

## 手动导出

FastMoss 网页版可导出 CSV 时优先导出；文件放到 `data/import/`，
由总控 skill 的 `normalize.py` 识别列名（中文 / 英文别名均支持）。
