## 项目结构
daily_ai_insight/
- data/
- reports/
  - charts/
- scripts/│   
- README.md
- CLAUDE.md

## 数据源说明

题目中给出了多个数据源，考虑到获取数据的时间成本，rss只挑了五个数据源，中文ai社区x2 + 英文ai社区x2 + ai社区型聚合站x1。
数据获取**参考了github项目[aihot](https://github.com/laolaoshiren/ai-hot)的新闻获取思路**，降低了本环节的时间和token消耗。
本项目当前提供一个 RSS 采集 MVP，脚本位于 `scripts/news_rss.py`，会抓取 `scripts/design.md` 中定义的 AI 信息源，经过黑名单、AI 白名单、3 天时间窗口、去重和排序后，写入 `data/news.json`, 该文件作为结构化抽取的原始物料。

## 输出结果示例

1. 结构化数据位于项目 `/data/structured_news.json`
2. 日报的可视化素材位于 `/reports/charts`
3. 日报本体位于 `/reports/ai_daily_report.html`

## 系统设计思路

1. 数据获取的设计思路请参考`scripts/design.md`，文档中已经给出详细的说明
2. 结构化抽取的设计思路请参考 `scripts/structure-process-design.md`, 内部清晰展示了新的数据schema的设计思路以及在后续分析中的用途
3. 日报分析的设计思路请参考 `reports/design.md`, 内部包含**日报内容分块**，**分析方式**和**可视化图标的使用**


## 核心流程说明

```text
数据源 
  -> rss获取为原始新闻 
  -> 结构化新闻
  -> 统计聚合
  -> Top 事件
  -> 趋势判断
  -> 风险/机会总结
  -> 可视化图表
  -> AI 日报
```

### 结构化新闻处理概要
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


## ai工具使用情况
1. 考虑到token的经济成本，本项目通过[codex & gpt5.5] + [claudecode + deepseek-v4-pro/kimi-k2.6]组合完成, 前者为我输出方案，后者执行
2. 在需求开发过程中，遵循 design - plan - progress状态监测 - 人工验收的闭环，避免agent执行漂移






