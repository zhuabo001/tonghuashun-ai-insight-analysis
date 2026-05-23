# RSS Python 开发计划

基于 `scripts/design.md`，本轮目标是实现一个稳定的 RSS 采集 MVP：抓取指定 AI 信息源，按规则清洗、过滤、去重，并维护项目根目录下的 `data/news.json`。本轮暂不实现日报分析、结构化评分和可视化输出。

## 技术栈选择

建议使用 **Python 脚本**，而不是 JS 脚本。

选择 Python 的原因：

1. RSS 抓取、文本清洗、过滤、去重和 JSON 写入属于典型离线数据处理任务，Python 更适合这类脚本。
2. Python 生态中的 `feedparser` 对 RSS/Atom 兼容性较好，可以降低不同站点 feed 格式差异带来的处理成本。
3. 时间处理、MD5、JSON、正则清洗、文件读写都可以主要依赖 Python 标准库完成，整体依赖较少。
4. 当前仓库没有 `package.json`、前端框架或 Node 项目结构，使用 JS 会额外引入 npm 初始化和依赖管理成本。
5. 后续如果继续实现日报分析、结构化抽取和图表生成，Python 更容易接入数据分析、NLP 和可视化工具链。

推荐技术栈：

```text
Python 3
feedparser
json / hashlib / datetime / re / pathlib
```

可选依赖：

```text
python-dateutil
```

第一版如果能通过 `feedparser` 的 `published_parsed` 满足发布时间解析，可以暂不引入 `python-dateutil`。

## 阶段 1：确定脚本入口和配置

新增脚本：

```text
scripts/news_rss.py
```

脚本职责：

- 定义 `RSS_SOURCES`
- 定义中文 AI 白名单
- 定义英文 AI 白名单
- 定义非 AI 黑名单
- 拉取 RSS
- 过滤、清洗、去重
- 写入 `data/news.json`

`RSS_SOURCES` 按 `scripts/design.md` 中的 schema 设计：

```python
{
    "name": "机器之心",
    "url": "https://www.jiqizhixin.com/feed",
    "lang": "zh",
    "priority": 1,
    "ai_only": True,
}
```

## 阶段 2：实现 RSS 拉取

实现流程：

1. 遍历 `RSS_SOURCES`
2. 使用 `feedparser.parse(url)` 拉取 feed
3. 每个源只处理前 10 条 entry

关于条数限制，采用文档后半部分的规则：**每个源最多 10 条**。文档前面流程图提到过 20 条，但后面的 `rule 5` 明确解释了 10 条的理由，并且最终 `news.json` 的总上限也是按 5 个 source 每源 10 条推导出来的。

## 阶段 3：实现文本清洗

实现函数：

```python
def clean_text(value: str, max_len: int | None = None) -> str:
    ...
```

处理规则：

- 输入为空时返回空字符串
- 去除 HTML 标签
- 替换常见 HTML 实体
- 压缩连续空白
- 去除首尾空白
- 摘要最多截断到 300 个字符

标题不截断，摘要截断。

## 阶段 4：实现过滤规则

实现函数：

```python
def is_ai_related(title: str, summary: str, lang: str, ai_only: bool) -> bool:
    ...
```

过滤顺序：

1. 黑名单优先，只要标题或摘要命中黑名单，直接过滤。
2. 中文源匹配中文 AI 白名单。
3. 英文源匹配英文 AI 白名单。
4. 聚合源也必须命中 AI 白名单。
5. 英文匹配统一转成大写后处理，保证大小写不敏感。

即使来源配置中的 `ai_only=True`，也不能直接放行。文档明确要求 AI 专用源也必须命中白名单，以避免广告、活动、招聘、泛科技内容混入。

## 阶段 5：实现时间过滤

只保留最近 3 天内的新闻。

规则：

- 如果 RSS entry 有 `published_parsed`，转成 datetime 后与 `now - 3 days` 比较。
- 早于 cutoff 的新闻跳过。
- 如果没有发布时间，不直接丢弃，`published` 设为 `None`。

排序时：

- 有 `published` 的新闻排在前面。
- 按发布时间从新到旧排序。
- `published=None` 的新闻放在后面。

## 阶段 6：生成稳定新闻 ID

实现函数：

```python
def generate_id(url: str) -> str:
    ...
```

规则：

- 使用 URL 计算 MD5。
- 截取前 12 位作为新闻 ID。
- 同一个 URL 永远生成同一个 ID。

如果 RSS entry 没有 link，建议跳过。没有 URL 时缺少稳定去重依据，也不适合作为最终新闻交付项。

## 阶段 7：合并已有数据并去重

目标文件：

```text
data/news.json
```

处理流程：

1. 如果 `data/news.json` 已存在，读取旧数据。
2. 将旧数据和新采集数据合并。
3. 按 `id` 去重。
4. 对合并后的所有数据重新应用当前清洗和过滤规则。
5. 按发布时间倒序排序。
6. 最多保留 80 条。
7. 写回 `data/news.json`。

关于数据上限，采用文档后半部分的 **80 条上限**，而不是流程图里的 300 条。当前项目是 MVP，且文档后面明确说明 80 条来自当前 source 数量和每源条数设计。

## 阶段 8：输出 JSON 格式

每条新闻结构：

```json
{
  "id": "url md5 前 12 位",
  "title": "清洗后的标题",
  "url": "原文链接",
  "source": "来源名称",
  "lang": "zh/en",
  "priority": 1,
  "published": "ISO 格式发布时间或 null",
  "summary": "清洗并截断后的摘要",
  "collected_at": "采集时间"
}
```

JSON 写入建议：

- UTF-8 编码
- `ensure_ascii=False`
- `indent=2`

这样方便中文阅读和后续调试。

## 阶段 9：增加运行反馈

脚本运行时打印简洁统计，例如：

```text
Fetching 5 RSS sources...
机器之心: fetched 10, accepted 4
量子位: fetched 10, accepted 6
TechCrunch AI: fetched 10, accepted 5
The Verge AI: fetched 10, accepted 3
Hacker News AI: fetched 10, accepted 2
Merged: old 42 + new 20 => final 55
Saved to data/news.json
```

运行反馈的目的：

- 快速判断 RSS 源是否失效。
- 判断过滤规则是否过严。
- 确认本轮新增数量和最终数据规模。

## 阶段 10：验证方案

第一版验证重点：

1. 脚本可重复运行，不产生重复新闻。
2. `data/news.json` 格式稳定。
3. 黑名单命中内容不会进入结果。
4. AI 白名单未命中的内容不会进入结果。
5. 旧数据会被新规则重新清洗。
6. 总数不超过 80。
7. 缺少发布时间的新闻不会导致脚本报错。

MVP 阶段优先保证主流程稳定可跑。后续可以再补充单元测试或 fixture 测试。

## 建议交付顺序

1. 新增 `scripts/news_rss.py`
2. 生成或更新 `data/news.json`
3. 在 `README.md` 中补充运行方式
4. 可选新增 `requirements.txt`

建议运行方式：

```bash
python3 scripts/news_rss.py
```

如果使用 `feedparser`，安装方式：

```bash
pip install feedparser
```

## 本轮边界

本轮只实现 RSS 抓取和 `data/news.json` 的稳定维护，不处理以下内容：

- 日报分析 engine
- 新闻重要性评分
- 情绪或风险机会判断
- 可视化图表
- 自动调度和消息推送

这些内容可以在 RSS 数据稳定后作为下一阶段开发任务继续推进。
