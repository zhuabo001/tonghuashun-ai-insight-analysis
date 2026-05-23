# AI 舆情分析日报系统实现计划

## 实现目标

基于现有 AI 新闻聚合功能，构建一个 **AI 舆情分析日报系统 MVP**。

第一版不做完整新闻站点，只做日报生成器。系统输入为 10-20 条近期 AI 新闻，输出包括：

- 原始数据文件
- 结构化新闻数据
- AI 分析日报
- 可视化图表
- 项目说明文档

核心目标是满足笔试题要求的 **结构化处理 + 分析过程 + 设计决策**，而不是只生成新闻摘要列表。

## 1. 确定 MVP 范围

MVP 不实现完整 Hugo 新闻站点，也不优先做自动化调度。

第一版重点完成：

- 选取 10-20 条 AI 相关新闻
- 标准化原始数据
- 设计结构化 Schema
- 对每条新闻进行结构化抽取
- 基于结构化结果生成日报分析
- 生成可视化结果
- 编写完整说明文档

## 2. 复用现有采集能力

优先复用当前项目已有的新闻聚合能力：

| 模块 | 用途 |
| --- | --- |
| `scripts/news_rss.py` | RSS 新闻采集、AI 关键词过滤、去重 |
| `scripts/news_api.py` | Hacker News、Reddit、V2EX 等社区信息采集 |
| `scripts/news_content_extract.py` | 新闻正文抽取 |
| `scripts/news_article_enhance.py` | 英文新闻中文化、正文清洗 |
| `scripts/news_interleave.py` | 来源多样性控制 |

如果时间紧，第一版可以直接从现有 `data/news.json` 中筛选最近 20 条新闻，避免爬虫稳定性影响 MVP 交付。

## 3. 设计项目输出目录

建议在项目中新增一个独立目录，例如：

```text
daily_ai_insight/
├── data/
│   ├── raw_news.json
│   ├── structured_news.json
│   └── report_data.json
├── reports/
│   ├── ai_daily_report.md
│   └── charts/
├── scripts/
│   ├── prepare_news.py
│   ├── structure_news.py
│   ├── generate_report.py
│   └── generate_charts.py
└── README.md
```

目录职责：

- `data/raw_news.json`：标准化后的原始新闻数据
- `data/structured_news.json`：AI/规则抽取得到的结构化结果
- `data/report_data.json`：日报生成所需的统计和中间数据
- `reports/ai_daily_report.md`：最终 AI 分析日报
- `reports/charts/`：可视化图表
- `scripts/`：各阶段处理脚本
- `README.md`：系统设计和运行说明

## 4. 准备原始数据

实现 `prepare_news.py`。

职责：

- 从现有 `data/news.json` 读取新闻
- 筛选最近、内容质量较好的 10-20 条
- 优先选择有 `content_text` 或有效 `summary` 的新闻
- 保证来源和语言尽量多样
- 标准化字段
- 输出 `daily_ai_insight/data/raw_news.json`

标准化字段建议包括：

```json
{
  "id": "...",
  "title": "...",
  "url": "...",
  "source": "...",
  "lang": "zh/en",
  "published": "...",
  "summary": "...",
  "content_text": "..."
}
```

## 5. 设计结构化抽取 Schema

结构化 Schema 示例：

```json
{
  "id": "...",
  "title": "...",
  "source": "...",
  "published": "...",
  "category": "模型发布/Agent/算力/应用/政策/资本/安全/其他",
  "entities": ["OpenAI", "NVIDIA"],
  "event_type": "产品发布/研究进展/融资并购/监管政策/安全风险/行业观点/其他",
  "importance_score": 8,
  "sentiment": "positive/neutral/negative",
  "key_facts": ["..."],
  "impact": "对行业的影响",
  "risk_or_opportunity": "潜在风险或机会",
  "evidence": "来自原文的依据"
}
```

字段设计理由：

- `category`：用于趋势统计和可视化
- `entities`：识别公司、产品、模型、人物等关键主体
- `event_type`：区分发布、融资、监管、研究、事故等事件类型
- `importance_score`：帮助选出 Top 3-5 重要事件
- `sentiment`：辅助舆情判断
- `key_facts`：保留事实依据，避免报告空泛
- `impact`：支撑深度总结
- `risk_or_opportunity`：满足风险或机会提示要求
- `evidence`：体现分析依据，降低幻觉风险

## 6. 实现结构化处理逻辑

实现 `structure_news.py`。

处理策略：

- 逐条或小批量读取 `raw_news.json`
- 对每条新闻使用规则 + AI Prompt 抽取结构化字段
- 不把全部原始数据一次性丢给 AI
- 每条结果独立保存，便于检查和重跑
- 输出 `structured_news.json`

Prompt 设计应要求 AI：

- 只基于给定新闻内容抽取
- 输出严格 JSON
- 不确定时使用 `其他` 或空数组
- `key_facts` 必须来自原文事实
- `impact` 和 `risk_or_opportunity` 需要有逻辑支撑

## 7. 增加结果校验

结构化结果生成后，需要做基础校验。

校验规则：

- `category` 必须在预设枚举范围内
- `event_type` 必须在预设枚举范围内
- `importance_score` 必须是 1-10 的整数
- `sentiment` 必须是 `positive`、`neutral` 或 `negative`
- `key_facts` 不能为空
- 缺失字段需要补默认值或标记 `needs_review`

校验目的：

- 保证结构化数据可被后续统计使用
- 避免 AI 输出格式漂移
- 体现处理过程和错误处理能力

## 8. 生成日报分析

实现 `generate_report.py`。

输入：

- `structured_news.json`

输出：

- `reports/ai_daily_report.md`
- `data/report_data.json`

日报内容包括：

- 今日 AI 领域 Top 3-5 重要事件
- 重要事件深度总结
- 技术、应用、政策、资本方向趋势判断
- 风险或机会提示
- 数据来源说明
- 处理流程说明

分析方式：

- 按 `importance_score` 选出重要事件
- 按 `category` 聚合趋势
- 按 `entities` 识别高频主体
- 结合 `key_facts`、`impact`、`risk_or_opportunity` 生成报告正文

## 9. 生成可视化

实现 `generate_charts.py`。

可视化形式不限，建议先做静态 PNG 或 SVG。

建议图表：

- 新闻类别分布
- 来源分布
- 重要性评分 Top 事件
- 可选：事件时间线

图表输出目录：

```text
daily_ai_insight/reports/charts/
```

日报 Markdown 中引用这些图表。

## 10. 编写说明文档

实现 `daily_ai_insight/README.md`。

必须覆盖：

- 项目目标
- 数据源说明
- 数据源选择理由
- 系统架构
- Schema 设计思路
- AI 使用方式
- Prompt 示例
- 清洗、分批处理、校验逻辑
- 可视化说明
- 如何运行
- 示例输出路径
- 当前限制和后续改进方向

说明文档是笔试题核心考察项，需要写清楚设计决策，而不只是放运行命令。

## 11. 最后验证交付物

本地跑完整流程，确认至少生成：

- `daily_ai_insight/data/raw_news.json`
- `daily_ai_insight/data/structured_news.json`
- `daily_ai_insight/data/report_data.json`
- `daily_ai_insight/reports/ai_daily_report.md`
- `daily_ai_insight/reports/charts/` 下至少一张图
- `daily_ai_insight/README.md`

同时检查：

- 原始数据是否达到 10-20 条
- 是否包含来源、时间、标题、摘要或正文
- 结构化字段是否完整
- 报告是否包含热点、深度总结、趋势判断、风险或机会
- 可视化是否能清晰传达信息
- README 是否解释了 AI 使用方式和处理流程

## 推荐实现策略

优先采用离线 MVP。

第一版直接基于现有 `data/news.json` 生成日报系统，避免把时间消耗在爬虫稳定性和自动化调度上。

优先级如下：

1. 数据筛选和标准化
2. 结构化 Schema 和抽取逻辑
3. 报告生成
4. 可视化
5. README 说明文档
6. 自动采集和调度

这样能最大程度满足笔试题要求，并保证在 1 天内交付一个完整、可运行、可解释的 MVP。
