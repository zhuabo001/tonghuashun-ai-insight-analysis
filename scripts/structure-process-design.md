# 结构化抽取 `news.json`

## 为什么要结构化抽取
- 原始数据质量不均匀，部分 summary 不是新闻摘要
- AI 容易混淆不同新闻的主体和事实
- 输出结果难以校验，也不方便生成图表
- 某条新闻抽取失败时无法独立重跑
- 报告结论缺少可追溯的中间数据

后续要进行分析以及可视化，原始数据的质量和维度可能撑不起来。

当分析的数据从 `news.json`变为`structured_news.json`后，后续就可以进行
```text
结构化新闻
  -> 统计聚合
  -> Top 事件
  -> 趋势判断
  -> 风险/机会总结
  -> 可视化图表
  -> AI 日报
```


## 原始数据的schema结构
```json
{
  "id": "...",
  "title": "...",
  "url": "...",
  "source": "...",
  "lang": "en",
  "priority": 1,
  "published": "...",
  "summary": "...",
  "collected_at": "..."
}
```

尤其是当前 `news.json`中，不同来源的 `summary` 质量并不一致：

- TechCrunch、The Verge、量子位等来源通常有较明确的新闻摘要
- Hacker News 来源的 `summary` 很多是社区热度信息，例如文章链接、评论链接、Points 和评论数，不一定是真正的新闻内容

因此，结构化抽取时不能简单把所有 `summary` 都当成正文事实使用，需要判断数据质量。

## 结构化schema设计

`data/structured_news.json`单挑数据的schema如下：
```json
{
  "id": "...",
  "title": "...",
  "url": "...",
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
  "evidence": "来自原文的依据",
  "data_quality": "high/medium/low",
  "needs_review": false
}
```
这里着重强调下`url`,`data_quality`,`needs_review`:
- `url` 用于在日报中引用原文，也方便人工核查
- `data_quality` 用于标记当前新闻内容是否足够支撑结构化判断
- `needs_review` 用于标记需要人工复核的新闻，避免低质量摘要被直接用于结论生成


### 各字段诞生的理由
#### 基础字段
这些字段主要从原始数据直接继承：
- `id`
- `title`
- `url`
- `source`
- `published`

这些字段解决的是“这条新闻来自哪里、什么时候发布、能否追溯”的问题。

#### `category`

`category` 用于表示新闻所属的 AI 领域方向, 具体分类有:
```text
模型发布 / Agent / 算力 / 应用 / 政策 / 资本 / 安全 / 其他
```
后续这些作为枚举值存在。这个字段只要是用来：
- 方便生成类别分布图
- 支撑日报中的趋势判断
- 帮助回答“今天 AI 领域主要热点集中在哪些方向”

举个例子：
- Google AI Search 相关问题可以归为 `应用`
- Trump 延迟 AI 安全行政令可以归为 `政策`
- DeepSeek Code 融资相关内容可以归为 `资本`

#### `entities`
用于抽取新闻中的关键主体，包括公司、产品、模型、人物、机构等, 预期其用于：
- 支撑高频实体统计
- 帮助识别当天被集中讨论的公司、产品或人物
- 后续日报可以基于实体生成“热点主体”分析
例如：

```json
["Google", "Spotify", "OpenAI", "DeepSeek", "Trump", "NTSB"]
```

#### `event_type`
用于表示新闻事件的性质，包含 ```产品发布 / 研究进展 / 融资并购 / 监管政策 / 安全风险 / 行业观点 / 其他```, 这些具体分类后续同样作为枚举值存在。
如果说 `category` 说明新闻属于哪个领域，那么`event_type` 说明这件事是什么类型， 同样是“应用”类新闻，可能是产品发布，也可能是安全风险或行业观点，如果要做日报分析，那么需要区分“发生了产品更新”“出现了监管变化”“暴露了风险”等不同事件。
依旧举例：
- Spotify AI remix 属于 `产品发布`
- AI startup inflated ARR 属于 `行业观点` 或 `融资并购` 相关风险
- AI security executive order 属于 `监管政策`

#### `importance_score`
`importance_score` 是 1-10 的整数，用于表示新闻重要性。
设计原因：

由于日报不能平均展示所有新闻，需要筛选 Top 3-5；并且后续报告可以按重要性排序，优先分析影响更大的事件；后续的可视化中可以生成重要事件排名图。

评分可以综合考虑：

- 主体影响力，例如 OpenAI、Google、NVIDIA、DeepSeek 等
- 事件影响范围，例如监管政策、安全事件、重要产品发布
- 来源优先级
- 社区热度，例如 Hacker News 的 Points 和评论数
- 新闻内容的确定性和完整性

特别注意：如果新闻内容不足，即使标题看起来很重要，也应该谨慎给分，并通过 `needs_review` 标记。

#### `sentiment`
该字段表示事件对 AI 行业舆情的倾向，```positive / neutral / negative```作为枚举值存在，这个字段是本题的核心，作为日报舆情判断的核心要素，同时可以帮助区分机会型新闻和风险型新闻。
注意，这里的 sentiment 不是文章作者语气，而是事件本身对行业的倾向：
- AI 产品发布通常偏 `positive` 或 `neutral`
- 安全事故、监管不确定性、成本失控通常偏 `negative` 或 `neutral`
- 行业观点类文章多数可以标为 `neutral`

#### `key_facts`
该字段的值来自标题、摘要或正文的关键事实列表。

设计原因：

- 避免结构化结果变成空泛判断
- 为后续报告提供可引用的事实材料
- 降低 AI 幻觉风险

要求：
- 必须来自原始新闻内容
- 不要加入无法从原文推出的信息
- 如果原文信息不足，应减少事实数量，并标记 `needs_review`

#### `impact`
`impact` 表示该新闻可能带来的行业影响。

设计原因：

- 原始新闻只回答“发生了什么”
- 日报还需要回答“这意味着什么”
- `impact` 是从新闻事实到趋势分析的桥梁

例如，AI 安全行政令推迟的影响可以写成：
```text
这反映出美国政府如何监管先进人工智能模型安全审查的持续不确定性
```


#### `risk_or_opportunity`
`risk_or_opportunity` 表示新闻中体现出的风险或机会。

设计原因：

- 满足日报对风险提示和机会判断的要求
- 让报告不只是新闻摘要，而是包含分析价值
- 帮助区分“利好”“风险”“政策不确定性”“商业机会”等方向

例如：

- AI remix 工具可能带来音乐创作机会，也可能带来版权风险
- AI 模型安全审查推迟可能降低短期合规压力，但增加政策不确定性

#### `evidence`

`evidence` 保存支持结构化判断的原文依据。

设计原因：

- 让结构化结果可追溯
- 方便人工复核
- 避免日报阶段凭空扩大结论

对于内容较短的新闻，`evidence` 可以直接使用标题或摘要中的关键句



#### `data_quality`

用于标记数据质量：

```text
high / medium / low
```

建议规则：

- `high`：有明确标题和有效摘要，摘要能支撑分类、事实和影响判断
- `medium`：标题信息较强，但摘要较短或不完整
- `low`：只有标题，或 summary 主要是链接、评论数、Points 等元数据

#### `needs_review`
`needs_review` 表示该条结构化结果是否需要人工复核.
设计原因：

- 当前原始数据并非每条都有正文
- 低质量摘要不应该直接进入最终分析结论


## 分批处理策略
题目明确要求结构化抽取阶段**不能**一次性把全部原始数据都交给agent，考虑到当前原始数据就30条左右，我可能会让agent然后按照 '1条/批'来处理，体现到代码中的话，`BATCH_SIZE`会被设置为1。这样一来，每条新闻独立处理，避免不同新闻之间的信息混淆，同时，更容易校验和人工检查，即使单条失败时只需要重跑这一条。

## 转换方式
对每条新闻，先构造一个只包含必要信息的输入：

```json
{
  "id": "90bacf183f61",
  "title": "Trump delays AI security executive order, saying language ‘could have been a blocker’",
  "url": "https://techcrunch.com/2026/05/21/trump-delays-ai-security-executive-order-i-dont-want-to-get-in-the-way-of-that-leading/",
  "source": "TechCrunch AI",
  "published": "2026-05-21T17:30:45+00:00",
  "summary": "President Trump delayed signing an executive order that would have required pre-release government security reviews of AI models, citing dissatisfaction with the order's language."
}
```

然后要求 AI 只基于该条新闻输出严格 JSON：
```json
{
  "id": "90bacf183f61",
  "title": "Trump delays AI security executive order, saying language ‘could have been a blocker’",
  "url": "https://techcrunch.com/2026/05/21/trump-delays-ai-security-executive-order-i-dont-want-to-get-in-the-way-of-that-leading/",
  "source": "TechCrunch AI",
  "published": "2026-05-21T17:30:45+00:00",
  "category": "政策",
  "entities": ["Trump", "AI models"],
  "event_type": "监管政策",
  "importance_score": 8,
  "sentiment": "neutral",
  "key_facts": [
    "Trump delayed signing an executive order related to AI security.",
    "The order would have required pre-release government security reviews of AI models."
  ],
  "impact": "This reflects ongoing uncertainty around how the US government may regulate advanced AI model safety reviews.",
  "risk_or_opportunity": "The delay may reduce immediate compliance pressure for AI companies, but also creates policy uncertainty around model safety oversight.",
  "evidence": "President Trump delayed signing an executive order that would have required pre-release government security reviews of AI models.",
  "data_quality": "high",
  "needs_review": false
}
```

## 低质量数据处理

当前有量子位新闻：

```text
title: 融资700亿！DeepSeek Code真要来了，ACM金牌大神崔添翼挂帅
summary: DeepSeek Code is Coming
```

这条新闻标题信息很强，但摘要太短。可以抽取出基础结构，但应标记需要复核：
```json
{
  "category": "资本",
  "entities": ["DeepSeek", "DeepSeek Code", "崔添翼"],
  "event_type": "融资并购",
  "importance_score": 7,
  "sentiment": "positive",
  "key_facts": [
    "标题提到 DeepSeek Code 即将到来。",
    "标题提到融资 700 亿以及崔添翼参与。"
  ],
  "impact": "If accurate, this suggests stronger capital and talent investment in AI coding products.",
  "risk_or_opportunity": "Opportunity lies in AI coding tool competition, but the short summary means the details need verification.",
  "evidence": "融资700亿！DeepSeek Code真要来了，ACM金牌大神崔添翼挂帅",
  "data_quality": "medium",
  "needs_review": true
}
```
这样做有几个好处：
- 可以保留标题中的有效线索
- 不把信息不足的新闻直接当成完全可靠事实
- 后续生成日报时可以降低这类新闻权重，或在报告中避免过度展开


对于 Hacker News 中只有链接、Points 和评论数的新闻，也可以类似处理：
- 如果标题足够明确，可以生成较保守的结构化结果
- 如果标题过于抽象，例如观点型标题，应标记 `data_quality: low`
- `needs_review` 应设为 `true`，或优先尝试用正文抽取脚本补充内容

## 针对结构化后的数据schema校验
输出后，需要做基础校验：

- `category` 必须属于预设枚举。
- `event_type` 必须属于预设枚举。
- `importance_score` 必须是 1-10 的整数。
- `sentiment` 必须是 `positive`、`neutral` 或 `negative`。
- `key_facts` 不能为空。
- `entities` 必须是数组。
- `data_quality` 必须是 `high`、`medium` 或 `low`。
- 缺失字段需要补默认值，或将 `needs_review` 标记为 `true`。

校验后的结果再写入 `structured_news.json`(这一步需要同步到后续的plan文档中作为agent行为准则)。


## 总结
整体转换流程如下：

```text
data/news.json
  -> 读取原始新闻
  -> 单条或小批量进行结构化抽取
  -> 校验结构化字段
  -> 合并保存 structured_news.json
  -> 后续基于 structured_news.json 生成日报和图表(本轮先不考虑日报和图表的生成)
```












