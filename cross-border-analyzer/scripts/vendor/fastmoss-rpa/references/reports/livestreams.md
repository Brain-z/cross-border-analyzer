# FastMoss 直播榜多维度分析报告

> This template is auto-filled by `scripts/analyze.py --out-md <path>`.  
> Curly-brace tokens like `{{country_table}}` are placeholders — do **not** rename them or `analyze.py` rendering will fail.  
> After generation, fill in the insight paragraphs (italics placeholders) by interpreting the tables.

**抓取时间**: {scrape_date} | **样本量**: {sample}

---

## 一、直播国家分布

| 国家 | 数量 | 占比 |
|---|---|---|
{country_table}

**核心洞察**: _（看东南亚占比、美区占比。直播榜反映"内容供给端"：东南亚直播间多但 GMV 低，美区直播间少但单价高）_

---

## 二、各榜单 × 国家交叉

**每行：榜单 | 总样本 | Top 3 国家 (含计数)**

{ranking_country_table}

**结构性洞察方向**：
1. 哪个榜单被某一国家垄断？（TT直播榜可能东南亚主导 = 流量便宜；直播带货达人榜美区强势 = GMV 高）
2. 哪些国家的直播间和带货能力都强？（综合型直播市场）
3. 哪些国家直播间多但带货弱？（流量 vs 商业化的差距）

---

## 三、跨榜重复实体（直播间/商品/达人）

{repeat_entities}

**洞察方向**：
- 同时进入多榜的实体是高价值目标
- 直播带货达人榜 × 直播爆品榜交叉：找到"带货达人 × 爆品"的强强组合

---

## 四、行动建议（模板）

| 角色 | 建议（根据上方数据填写）|
|---|---|
| **品牌方** | _（按目标市场找头部直播间合作；优先跨榜达人）_ |
| **MCN** | _（找直播带货达人榜 + 直播爆品榜双榜达人签约）_ |
| **跨境商家** | _（盯直播爆品榜发现爆款，快速跟进选品）_ |
| **直播运营** | _（学习 TT直播榜 头部直播间的开播时长/时段策略）_ |

---

## 报告复现命令

```bash
python <path-to-skill>/scripts/analyze.py \\
    --tiktok <out-dir>/tiktok.csv \\
    --hot-product <out-dir>/hot_product.csv \\
    --live-commerce <out-dir>/live_commerce.csv \\
    --out-md <report>.md
```

`<path-to-skill>` = the directory holding this skill's `SKILL.md` (`.workbuddy/skills/fastmoss-rpa` for project install, `~/.workbuddy/skills/fastmoss-rpa` for user install).
