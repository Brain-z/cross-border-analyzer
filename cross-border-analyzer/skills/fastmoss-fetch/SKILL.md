---
name: fastmoss-fetch
description: "从 FastMoss（fastmoss.com）抓取 TikTok Shop 榜单数据：商品 / 达人 / 店铺 / 广告 / 素材 / 直播 / 品类大盘。优先用 bsk 驱动已登录浏览器，降级用内嵌浏览器，再降级引导手动导出 CSV。当需要获取 FastMoss 榜单或市场数据时使用。"
---

# FastMoss 数据抓取

把用户需求映射成抓取任务并落盘为 CSV（UTF-8 BOM）到 `data/raw/`。
抓取逻辑**直接复用社区工具** `scripts/vendor/fastmoss-rpa/fastmoss_rpa.py`
（覆盖商品 / 达人 / 店铺 / 广告 / 素材 / 直播 / 品类大盘 7 大模块），不自己重写。

## 前置条件

- 用户有一个已登录 FastMoss 的浏览器会话（专业版账号数据最完整）；
- bsk（BrowserSkill）是社区抓取工具的执行引擎，需要先安装并连接；
- 社区工具的命令细节、字段与排错见
  `scripts/vendor/fastmoss-rpa/UPSTREAM_SKILL.md` 和
  `scripts/vendor/fastmoss-rpa/references/environment.md`。

## 抓取命令（社区工具）

从插件根目录执行。**分工**：商品榜的"新品 / 销量榜单 + 月榜 / 日期范围 +
国家与品类组合"用薄适配器 `scripts/fastmoss_filtered.py`（社区工具一次只能筛一个维度，
且只覆盖新品榜）；达人 / 店铺 / 广告 / 素材 / 直播 / 品类大盘用社区工具。

```bash
# 商品榜（新品 / 销量，国家、品类、时间范围全部走参数，禁止改脚本源码）
python3 scripts/fastmoss_filtered.py --board new --pages 5 \
  --country 英国 --category 美妆个护 --start 2026-07-01 --end 2026-07-31 \
  --session <bsk-session> --out data/raw/products_new_gb.csv

python3 scripts/fastmoss_filtered.py --board sales --pages 5 \
  --country 美国 --category 时尚配件 --time-label 月榜 \
  --session <bsk-session> --out data/raw/products_sales_us.csv

# 参数说明：--country/--category 按页面标签写；--start/--end 仅新品榜生效
# （不填默认近 30 天）；--time-label 仅销量榜生效（月榜/周榜/日榜，默认月榜）。

# 达人 / 店铺 / 广告 / 素材 / 直播榜
python3 scripts/vendor/fastmoss-rpa/fastmoss_rpa.py scrape \
  --section creators --ranking fans --pages 3 --out data/raw/creators.csv

# 品类大盘（走页面 JSON 接口，region 用代码）
python3 scripts/vendor/fastmoss-rpa/fastmoss_rpa.py market base \
  --region US --out data/raw/us_market.json \
  --top-products-csv data/raw/us_top_products.csv
```

"国家 + 品类"组合一次筛不出时，分两次抓取再合并去重。
社区工具还提供 `analyze` 子命令可生成快速洞察报告（本插件默认输出走自研评分管道）。

## 抓取降级链

1. **社区工具（bsk CLI）**：`bsk status` 确认 `browsers connected ≥ 1` 后直接跑上面的命令；
2. **Codex 内嵌浏览器**：导航到 FastMoss 对应榜单页 → 应用筛选（地区/品类/时间）→ 翻页 → 提取表格 → 保存 CSV（此时不走社区工具）；
3. **手动导入**：提示用户在 FastMoss 网页导出 CSV，放到 `data/import/`，告知文件名后继续分析。

## 榜单映射

| 模块 | 子榜单 | 筛选 |
|---|---|---|
| products 商品榜 | 新品 / 销量 / 热推 | 国家、品类、店铺类型 |
| creators 达人榜 | 涨粉 / 带货 / 蓝V / 热门 / 黑马 | 国家、时间 |
| shops 店铺榜 | 销量 / 热推 | 国家 |
| ads 广告趋势 | 标签 / 关键词 / 品类 | 国家、时间 |
| creatives 素材榜 | 视频 / 音乐 / 标签 | 国家、时间 |
| livestreams 直播榜 | TT直播 / 直播爆品 / 直播达人 | 国家、时间 |
| market 品类大盘 | 行业格局 / 市场总览 / 日销趋势 | 国家、时间 |

参数转换：

- 国家：中文 ↔ ISO 代码（美国=US、印尼=ID、英国=GB……）；
- 时间：日榜 / 周榜 / 月榜；
- 品类：先查 [references/categories.md](../../references/categories.md) 的种子映射，匹配不到走模糊搜索；
  抓取完成后把数据里实际出现的品类记录下来，作为后续分析和回填映射表的依据（不写死）；
- "国家 + 品类"组合：FastMoss 一次只能筛一种时，分两次抓取再合并去重。

## 提取技巧

- 读表格：动态读 `<thead>` 表头，字段自适应，FastMoss 改列名不用改代码；
- 定位控件用 `bsk snapshot` 的文本引用，点击/翻页用文本标签选择器，避免快照 ref 过期；
- 字段说明见 [references/fastmoss-fields.md](../../references/fastmoss-fields.md)，
  完整的 API 契约见 `scripts/vendor/fastmoss-rpa/references/api_notes.md`。

## 排错

- 抓到 0 行：翻页太快，加 `--nav-sleep 6 --page-sleep 4` 加大等待；
- `bsk status` 无浏览器连接：确认扩展弹窗已变绿、fastmoss.com 已登录；
- 字段为空：多为套餐权限限制，保留原样，不编造；
- 其余见上游 `UPSTREAM_SKILL.md` 的 gotchas（SPA 等待、JS 转义、编码等）。

## Token 预算（强制）

- 抓取只运行脚本，落盘后**不读 CSV 全文**；用 `wc -l <out>` 确认行数即可。
- 不要逐页 `evaluate` 打印表格内容；脚本输出就是最终结果。
- 失败按上方排错清单一次排查、一次重试，禁止同一命令反复试错。
- bsk 的 daemon/编码/路径问题脚本已自动处理，不要为此展开调查。
