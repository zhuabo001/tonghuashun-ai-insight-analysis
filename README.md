# 项目结构
daily_ai_insight/
├── data/
├── reports/
│   └── charts/
├── scripts/│   
└── README.md

# 数据源说明

## [选取的数据源]

### [选择的理由]


#系统设计思路
每条消息有同样的字段，每个字段有不同的**重要性权重**。

## 消息源字段设计

## 重要性权重的依据

## 重要性权重较高的字段

## (可选，有时间就做)定时任务 + 消息推送
本功能为各类claw而设计，不在mvp版本中

# 核心流程说明

1. 从[选取的数据源]抓取了中、英文信息各10条
2. 设计字段，为后续的分析和可视化打下基础
3. 针对上一步设计好的字段进行综合评判，不同字段会对应不同的**重要性权重**
4. **重要性权重**权值在前四的字段值得拥有对应的可视化分析报告
5. 综合所有字段的 **重要性权重** 的值，选取top3-5个热点消息

# RSS 采集脚本

本项目当前提供一个 RSS 采集 MVP，脚本位于 `scripts/news_rss.py`，会抓取 `scripts/design.md` 中定义的 AI 信息源，经过黑名单、AI 白名单、3 天时间窗口、去重和排序后，写入 `data/news.json`。

## 安装依赖

建议使用项目内虚拟环境：

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## 运行方式

```bash
.venv/bin/python scripts/news_rss.py
```

输出文件：

```text
data/news.json
```

脚本会打印每个 RSS 源的抓取数量、通过过滤数量，以及最终合并后的新闻总数。

# 结构化新闻处理

结构化处理脚本位于 `scripts/structure_news.py`，输入为 `data/news.json`，输出为 `data/structured_news.json`。

```bash
.venv/bin/python scripts/structure_news.py
```

结构化阶段固定按 `BATCH_SIZE = 1` 单条处理新闻，避免不同新闻之间的主体和事实互相混淆。输出的单条结构命名为 `StructuredNewsItem`，包含基础追溯字段、分类字段、舆情字段、事实依据字段，以及 `data_quality` 和 `needs_review` 两个质量控制字段。

校验后的结果才会写入 `data/structured_news.json`。校验规则包括：

- `category`、`event_type`、`sentiment`、`data_quality` 必须属于预设枚举。
- `importance_score` 必须是 1-10 的整数。
- `entities` 必须是数组。
- `key_facts` 必须非空。
- 缺失字段会补默认值，并将 `needs_review` 标记为 `true`。

需要特别注意的是，Hacker News 的 `summary` 通常包含 Article URL、Comments URL、Points 和评论数等社区元数据，不能直接当作正文事实使用；量子位等短摘要新闻也会被保守标记为 `medium` 或 `low` 数据质量，并优先进入人工复核。
