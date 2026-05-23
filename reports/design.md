# reports-design

## 数据源
请使用 `data/structured_news.json`中的数据进行日报分析

## 产物
一份位于当前目录下的名为 `ai_daily_report.html`的html文件，页面上的内容需要包含：
- 今日 AI 领域 Top 3-5 重要事件
- 重要事件深度总结
- 技术、应用、政策、资本方向趋势判断
- 风险或机会提示
- 数据来源说明
- 处理流程说明

## 分析方式
1. 按 `importance_score` 选出重要事件
2. 按 `category` 聚合趋势
3. 按 `entities` 识别高频主体
4. 结合 `key_facts`、`impact`、`risk_or_opportunity` 生成报告正文

## 可视化图表
形式暂时不限(题目中没明说)，可以先做静态的png或者svg。
需要包含以下图表类别：
- 新闻类别分布
- 来源分布
- 重要性评分 Top 事件

如果可以额外加上事件时间线那就更无敌了。

图标先作为独立的素材存于当前目录下的`/charts`目录下。后`ai_daily_report.html`可以引用这些素材。

