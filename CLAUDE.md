# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

AI舆情分析日报系统（Daily AI Insight Engine）—— 从每日 AI 新闻中提取结构化洞察，生成可读分析报告与可视化结果。这是一个笔试题项目，核心约束：**不能把原始数据丢给 AI 全量生成**，必须体现处理逻辑。

## 三阶段 Pipeline

```
RSS采集(scripts/news_rss.py) → 结构化抽取(scripts/structure_news.py) → 报告生成(reports/generate_report.py)
```

数据流：`data/news.json` → `data/structured_news.json` → `reports/ai_daily_report.html` + `reports/charts/*.png`

## 运行命令

```bash
# 环境准备（macOS 上需 --break-system-packages 或使用 venv）
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Pipeline
.venv/bin/python scripts/news_rss.py          # 采集 RSS → data/news.json
.venv/bin/python scripts/structure_news.py    # 结构化抽取 → data/structured_news.json
.venv/bin/python reports/generate_report.py   # 分析 + 图表 + HTML → reports/
```

## 关键架构决策

### 结构化 Schema（`StructuredNewsItem`）
每条新闻包含：基础追溯（id/title/url/source/published）、分类（category/event_type/sentiment/importance_score）、事实依据（key_facts/impact/risk_or_opportunity/evidence）、质量控制（data_quality/needs_review）。

### 数据质量分级
- `high`：来自 TechCrunch/The Verge 等，摘要含实际正文内容，可直接用于深度分析
- `medium`：摘要较短但非元数据，保守使用，优先人工复核
- `low`：Hacker News 仅标题或摘要含社区元数据（Points/Comments URL），仅参与分布统计，不进入深度分析

### Hacker News 元数据隔离
HN 的 summary 常包含 "Points: 216"、"Comments URL:" 等社区元数据而非正文。`structure_news.py` 中通过 `inference_text()` 函数集中判断是否使用 summary：若 summary 为空或含 HN 元数据特征，分类/实体/情感/评分仅基于标题推断。

### BATCH_SIZE = 1
结构化抽取按单条处理，避免不同新闻间的实体和事实互相混淆。

### RSS 过滤优先级
黑名单 > 时间过滤(3天) > AI 白名单。即使信源标记为 `ai_only=true`，仍需命中 AI 白名单才能入库。

### 报告生成：纯 Python 规则引擎
按设计文档约束，报告的分析逻辑不使用 LLM：importance_score 排序取 Top 5、Counter 聚合类别/来源/实体分布、规则引擎生成趋势语句、规则过滤风险/机会条目。图表用 matplotlib 生成静态 PNG。
