# FastMoss 店铺榜多维度分析报告

> This template is auto-filled by `scripts/analyze.py --out-md <path>`.  
> Curly-brace tokens like `{{country_table}}` are placeholders — do **not** rename them or `analyze.py` rendering will fail.  
> After generation, fill in the insight paragraphs (italics placeholders) by interpreting the tables.

**抓取时间**: {scrape_date} | **样本量**: {sample}

---

## 一、店铺品类分布

| 品类 | 数量 | 占比 |
|---|---|---|
{category_table}

**核心洞察**: _（看品类集中度：哪些品类店铺多 = 红海竞争；哪些少但销量高 = 蓝海机会）_

---

## 二、店铺国家分布（如使用 --country 过滤）

| 国家 | 数量 | 占比 |
|---|---|---|
{country_table}

**洞察方向**：
- 哪些国家店铺供给充足（适合找合作店铺）
- 哪些国家店铺少但单店 GMV 高（地缘机会）
- 东南亚店铺（ID/MY/TH/PH/VN）多 = 跨境入门；美区少但单价高

---

## 三、各榜单 × 品类交叉

**每行：榜单 | 总样本 | Top 3 品类 (含计数)**

{ranking_category_table}

**结构性洞察方向**：
1. 哪个品类在销量榜和热推榜都强势？（规模化 + 增长动能兼具）
2. 哪些品类只出现在热推榜 = 新爆发趋势？
3. 哪些品类销量高但没新增动销 = 存量市场？

---

## 四、跨榜重复店铺

{repeat_shops}

**洞察方向**：
- 同时进入销量榜 + 热推榜的店铺是综合实力最强的目标
- 单榜单高频出现 = 持续运营良好

---

## 五、行动建议（模板）

| 角色 | 建议（根据上方数据填写）|
|---|---|
| **品牌方** | _（按品类找头部店铺；优先跨榜店铺合作）_ |
| **商家** | _（找品类空白市场切入；对标热推榜学习打法）_ |
| **跨境运营** | _（盯热推榜发现新晋店铺作为潜在合作对象）_ |

---

## 报告复现命令

```bash
python <path-to-skill>/scripts/analyze.py \\
    --sales <out-dir>/sales.csv \\
    --hot <out-dir>/hot.csv \\
    --out-md <report>.md
```

`<path-to-skill>` = the directory holding this skill's `SKILL.md` (`.workbuddy/skills/fastmoss-rpa` for project install, `~/.workbuddy/skills/fastmoss-rpa` for user install).
