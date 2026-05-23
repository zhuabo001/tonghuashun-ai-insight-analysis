# `news.json` 结构化处理实现方案

## Summary

基于 `scripts/structure-process-design.md`，新增一个结构化处理阶段：读取 `data/news.json`，按 `BATCH_SIZE = 1` 逐条抽取结构化字段，校验后写入 `data/structured_news.json`。本阶段只处理结构化数据，不生成日报和图表。

核心原则：

- 不一次性把全部新闻交给 AI，避免不同新闻事实混淆。
- 所有判断必须可追溯到当前单条新闻的 `title`、`summary`、`url` 等字段。
- 对低质量新闻保守抽取，并通过 `data_quality` 和 `needs_review` 明确标记。
- 对文档中“特别注意 / 注意”的约束作为实现规则，不只是说明文字。

## Schema Names And Roles

结构化单条数据命名为 `StructuredNewsItem`，输出文件为 `data/structured_news.json`。

字段职责如下：

- `id`：继承原始新闻 ID，用于去重、增量合并和单条重跑。
- `title`：继承原始标题，是事实抽取的主要依据之一。
- `url`：继承原文链接，用于日报引用和人工复核；这是重点字段，必须保留。
- `source`：继承来源，用于来源统计和质量判断。
- `published`：继承发布时间，用于排序和时间线分析。
- `category`：AI 领域方向枚举，取值为 `模型发布 / Agent / 算力 / 应用 / 政策 / 资本 / 安全 / 其他`。
- `entities`：关键主体数组，包括公司、产品、模型、人物、机构等。
- `event_type`：事件性质枚举，取值为 `产品发布 / 研究进展 / 融资并购 / 监管政策 / 安全风险 / 行业观点 / 其他`。
- `importance_score`：1-10 整数，表示新闻重要性；特别注意，内容不足时即使标题重要也要谨慎给分，并标记 `needs_review`。
- `sentiment`：事件对 AI 行业舆情的倾向，取值为 `positive / neutral / negative`；注意这里不是作者语气，而是事件本身对行业的影响倾向。
- `key_facts`：来自原始标题或摘要的事实列表，不能为空；不得加入无法从原文推出的信息。
- `impact`：基于事实推导出的行业影响，必须和 `key_facts` 有逻辑关联。
- `risk_or_opportunity`：新闻体现出的风险或机会，用于后续日报分析。
- `evidence`：支撑结构化判断的原文依据，可直接使用标题或摘要关键句。
- `data_quality`：数据质量枚举，取值为 `high / medium / low`；这是重点字段，用于判断结构化结果可信度。
- `needs_review`：布尔值；这是重点字段，用于标记需要人工复核的新闻，避免低质量摘要直接进入结论生成。

## Implementation Changes

新增 `scripts/structure_news.py`，职责是完成读取、单条抽取、校验、合并保存。

实现流程：

1. 从 `data/news.json` 读取原始新闻。
2. 将每条新闻转换为最小输入对象：`id`、`title`、`url`、`source`、`published`、`summary`。
3. 使用 `BATCH_SIZE = 1` 逐条处理，严格遵守设计文档中“不能一次性把全部原始数据都交给 agent”的要求。
4. 对每条新闻生成 `StructuredNewsItem`。
5. 对结构化结果执行 schema 校验。
6. 校验通过或补默认值后，写入 `data/structured_news.json`。
7. 保持固定输出顺序，便于 diff、复核和单条追踪。

低质量处理规则：

- TechCrunch、The Verge 等有有效摘要的新闻通常可评为 `high` 或 `medium`。
- 量子位这类标题强但摘要很短的新闻通常评为 `medium`，并设置 `needs_review: true`。
- Hacker News 如果 `summary` 主要包含 `Article URL`、`Comments URL`、`Points`、`# Comments`，不能当作正文事实；标题明确时保守抽取，通常设为 `low` 或 `medium`，并设置 `needs_review: true`。
- 如果标题也过于抽象，例如纯观点标题，`key_facts` 只写可确认事实，`importance_score` 不应因社区热度被过度抬高。

校验规则：

- `category` 必须属于预设枚举，否则改为 `其他` 并标记 `needs_review: true`。
- `event_type` 必须属于预设枚举，否则改为 `其他` 并标记 `needs_review: true`。
- `importance_score` 必须是 1-10 整数，否则截断或设为保守默认值。
- `sentiment` 必须是 `positive / neutral / negative`，否则设为 `neutral` 并标记复核。
- `entities` 必须是数组。
- `key_facts` 必须非空；如果无法抽取，则使用标题作为最小事实依据，并标记复核。
- `data_quality` 必须是 `high / medium / low`。
- 缺失字段补默认值，同时设置 `needs_review: true`。
- 校验后的结果再写入 `structured_news.json`，并把这条行为准则同步到后续计划或 README 中。

## Test Plan

- 运行结构化脚本后确认生成 `data/structured_news.json`。
- 校验输出条数与 `data/news.json` 一致，当前应为 29 条。
- 校验每条记录都包含完整 `StructuredNewsItem` 字段。
- 校验枚举字段没有非法值。
- 校验 `importance_score` 全部为 1-10 整数。
- 校验 `key_facts` 不为空。
- 抽查 Hacker News 新闻，确认不会把 Points、评论数当成正文事实，并且大多 `needs_review: true`。
- 抽查量子位短摘要新闻，确认 `data_quality` 不会被误判为 `high`。
- 抽查 `sentiment`，确认判断的是事件对 AI 行业的倾向，而不是文章作者语气。

## Assumptions

- 本阶段输出只到 `data/structured_news.json`，不生成日报、统计聚合或图表。
- 使用当前 `data/news.json` 作为输入，不重新抓取 RSS。
- 若没有接入外部 AI API，第一版可由 agent 按单条新闻生成结构化 JSON，再由脚本负责校验和落盘；若后续接入 API，仍保持同一 schema 和校验规则。
- `data_quality` 和 `needs_review` 是后续日报阶段的重要控制字段，低质量或需复核新闻不得被无条件用于强结论。
