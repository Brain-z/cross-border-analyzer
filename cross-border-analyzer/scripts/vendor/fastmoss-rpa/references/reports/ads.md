# FastMoss 广告趋势榜多维度分析报告

> This template is auto-filled by `scripts/analyze.py --out-md <path>`.  
> Curly-brace tokens like `{{country_table}}` are placeholders — do **not** rename them or `analyze.py` rendering will fail.  
> After generation, fill in the insight paragraphs (italics placeholders) by interpreting the tables.

**抓取时间**: {scrape_date} | **样本量**: {sample}

---

## 一、广告趋势国家分布

| 国家 | 数量 | 占比 |
|---|---|---|
{country_table}

**核心洞察**: _（标签/关键词/品类的"火"地域分布。趋势榜反映"流量方向标"：哪些市场的投流话题正在爆发）_

---

## 二、各榜单 × 国家交叉

**每行：榜单 | 总样本 | Top 3 国家 (含计数)**

{ranking_country_table}

**结构性洞察方向**：
1. 哪个国家的关键词/品类同时强势？（综合趋势市场）
2. 标签榜的"地域集中度"反映话题传播模式
3. 哪些国家的关键词多 = 投流竞争激烈；少 = 蓝海

---

## 三、跨榜重复实体（标签/关键词/品类）

{repeat_entities}

**洞察方向**：
- 同一个标签 / 关键词同时进入多榜 = 高潜力投放素材
- 品类×关键词交叉：找到"品类热度 + 关键词热度"的强组合

---

## 四、行动建议（模板）

| 角色 | 建议（根据上方数据填写）|
|---|---|
| **投手** | _（采用热门标签+热门关键词组合，提升 CTR）_ |
| **选品** | _（参考热门品类趋势发现新机会）_ |
| **品牌方** | _（关注标签洞察的品牌心智构建）_ |

---

## 报告复现命令

```bash
python <path-to-skill>/scripts/analyze.py \\
    --tag <out-dir>/tags.csv \\
    --keyword <out-dir>/keywords.csv \\
    --category <out-dir>/categories.csv \\
    --out-md <report>.md
```

`<path-to-skill>` = the directory holding this skill's `SKILL.md` (`.workbuddy/skills/fastmoss-rpa` for project install, `~/.workbuddy/skills/fastmoss-rpa` for user install).
