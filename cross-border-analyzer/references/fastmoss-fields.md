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

## 提取 JS（bsk evaluate 用）

FastMoss 页面结构会变，优先读表头做字段自适应：

```js
(() => {
  const tables = Array.from(document.querySelectorAll('table'));
  if (!tables.length) return { error: 'no table found' };
  const rows = [];
  for (const t of tables) {
    for (const tr of t.querySelectorAll('tr')) {
      const cells = Array.from(tr.querySelectorAll('th,td')).map(c => c.innerText.trim());
      if (cells.length) rows.push(cells);
    }
  }
  return { rows };
})()
```

保存输出 JSON 后转 CSV：

```bash
python3 scripts/fastmoss_fetch.py json2csv table.json data/raw/products.csv
```

## 更稳的替代：页面 JSON 接口

打开开发者工具 Network，过滤 `api` / `json`，榜单数据往往来自同源 JSON 接口。
在 `bsk evaluate` 里直接 `fetch()` 该接口可免翻页，返回 JSON 用上面命令落盘。

## 手动导出

FastMoss 网页版可导出 CSV 时优先导出；文件放到 `data/import/`，
由总控 skill 的 `normalize.py` 识别列名（中文 / 英文别名均支持）。
