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
