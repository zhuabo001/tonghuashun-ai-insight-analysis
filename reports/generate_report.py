"""
AI 舆情分析日报生成脚本
处理流程：数据加载 → 统计分析 → 图表生成 → HTML 报告组装
"""

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# ── 路径常量 ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "structured_news.json"
CHARTS_DIR = Path(__file__).parent / "charts"
REPORT_PATH = Path(__file__).parent / "ai_daily_report.html"


# ══════════════════════════════════════════════════════════════════════════════
# Step 1: 数据加载与预处理
# ══════════════════════════════════════════════════════════════════════════════

def load_news(path: Path) -> tuple[list[dict], list[dict]]:
    """
    加载结构化新闻数据，返回 (all_items, quality_items)。
    quality_items 排除 data_quality=="low" 的条目，用于深度分析。
    两个列表均按 importance_score 降序排列。
    """
    with open(path, encoding="utf-8") as f:
        items = json.load(f)

    required_fields = {
        "id", "title", "source", "published", "category",
        "importance_score", "sentiment", "entities",
        "key_facts", "impact", "risk_or_opportunity",
        "event_type", "data_quality",
    }
    valid = [item for item in items if required_fields.issubset(item.keys())]

    all_sorted = sorted(valid, key=lambda x: x["importance_score"], reverse=True)
    quality_sorted = [i for i in all_sorted if i.get("data_quality") != "low"]

    return all_sorted, quality_sorted


# ══════════════════════════════════════════════════════════════════════════════
# Step 2: 统计分析
# ══════════════════════════════════════════════════════════════════════════════

def analyze(all_items: list[dict], quality_items: list[dict]) -> dict:
    """
    对新闻数据做全量统计分析，返回结构化分析结果字典。
    all_items  用于分布统计（类别/来源/情感）。
    quality_items 用于 Top 事件、实体频率、趋势判断。
    """
    # Top 重要事件：quality 数据中 importance_score >= 8，最多取 5 条
    top_events = [i for i in quality_items if i["importance_score"] >= 8][:5]
    if len(top_events) < 3:
        top_events = quality_items[:5]

    # 类别分布（全量）
    category_dist = Counter(i["category"] for i in all_items)

    # 来源分布（全量）
    source_dist = Counter(i["source"] for i in all_items)

    # 情感分布（全量）
    sentiment_dist = Counter(i["sentiment"] for i in all_items)

    # 高频实体（quality 数据，展平后计数，取 Top 10）
    all_entities: list[str] = []
    for item in quality_items:
        all_entities.extend(item.get("entities", []))
    entity_freq = Counter(all_entities).most_common(10)

    # 趋势分析：按 category 分组，统计 sentiment 比例和事件数
    trend_categories = {
        "模型发布": "技术",
        "应用":   "应用",
        "政策":   "政策",
        "资本":   "资本",
    }
    trends: dict[str, dict] = {}
    for cat, label in trend_categories.items():
        group = [i for i in all_items if i["category"] == cat]
        if not group:
            trends[label] = {"count": 0, "label": label, "category": cat,
                             "positive": 0, "negative": 0, "neutral": 0,
                             "entities": [], "summary": "暂无相关新闻"}
            continue
        sent = Counter(i["sentiment"] for i in group)
        ents: list[str] = []
        for i in group:
            ents.extend(i.get("entities", []))
        top_ents = [e for e, _ in Counter(ents).most_common(3)]
        trends[label] = {
            "count": len(group),
            "label": label,
            "category": cat,
            "positive": sent.get("positive", 0),
            "negative": sent.get("negative", 0),
            "neutral":  sent.get("neutral", 0),
            "entities": top_ents,
            "summary":  _trend_summary(label, len(group), sent),
        }

    # 风险条目：负面情感 或 安全/政策类别 或 安全风险事件类型
    risks = [
        i for i in quality_items
        if i["sentiment"] == "negative"
        or i["category"] in {"安全", "政策"}
        or i["event_type"] == "安全风险"
    ][:6]

    # 机会条目：正面情感 或 产品发布/融资并购
    opportunities = [
        i for i in quality_items
        if i["sentiment"] == "positive"
        or i["event_type"] in {"产品发布", "融资并购"}
    ][:6]

    # 数据质量分布（全量）
    quality_dist = Counter(i.get("data_quality", "unknown") for i in all_items)

    # 时间线数据：每条 quality 新闻的发布时间 + 重要性评分
    timeline = []
    for item in quality_items:
        try:
            dt = datetime.fromisoformat(item["published"])
            timeline.append({
                "dt": dt,
                "score": item["importance_score"],
                "title": item["title"],
                "source": item["source"],
            })
        except (ValueError, KeyError):
            pass
    timeline.sort(key=lambda x: x["dt"])

    return {
        "top_events":     top_events,
        "category_dist":  category_dist,
        "source_dist":    source_dist,
        "sentiment_dist": sentiment_dist,
        "entity_freq":    entity_freq,
        "trends":         trends,
        "risks":          risks,
        "opportunities":  opportunities,
        "quality_dist":   quality_dist,
        "timeline":       timeline,
        "total":          len(all_items),
        "quality_total":  len(quality_items),
    }


def _trend_summary(label: str, count: int, sent: Counter) -> str:
    total = sum(sent.values()) or 1
    neg_ratio = sent.get("negative", 0) / total
    pos_ratio = sent.get("positive", 0) / total

    if count == 0:
        return "暂无相关新闻。"
    if neg_ratio >= 0.6:
        return f"共 {count} 条相关新闻，负面信号占主导（{neg_ratio:.0%}），需关注潜在风险。"
    if pos_ratio >= 0.5:
        return f"共 {count} 条相关新闻，整体呈积极态势（{pos_ratio:.0%} 正面），发展势头良好。"
    return f"共 {count} 条相关新闻，情绪较为中性，市场处于观望阶段。"


# ══════════════════════════════════════════════════════════════════════════════
# Step 3: 图表生成（matplotlib）
# ══════════════════════════════════════════════════════════════════════════════

def _setup_matplotlib():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    # CJK 字体：macOS 优先 PingFang SC，Linux 回退 DejaVu Sans
    plt.rcParams["font.sans-serif"] = ["Hiragino Sans GB", "STHeiti", "PingFang HK", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    return plt


def _truncate(text: str, max_len: int = 28) -> str:
    return text if len(text) <= max_len else text[:max_len] + "…"


PALETTE = ["#4C72B0", "#55A868", "#C44E52", "#8172B2", "#CCB974",
           "#64B5CD", "#E07B54", "#76B7B2", "#F28E2B", "#B07AA1"]


def generate_charts(analysis: dict, charts_dir: Path) -> dict[str, Path]:
    """生成 4 张图表，返回 {name: path} 字典。"""
    charts_dir.mkdir(parents=True, exist_ok=True)
    plt = _setup_matplotlib()
    paths: dict[str, Path] = {}

    # ── 图表 1：类别分布饼图 ──────────────────────────────────────────────────
    cat_dist = analysis["category_dist"]
    if cat_dist:
        fig, ax = plt.subplots(figsize=(7, 5))
        labels = list(cat_dist.keys())
        sizes  = list(cat_dist.values())
        colors = PALETTE[:len(labels)]
        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, colors=colors,
            autopct="%1.1f%%", startangle=140,
            pctdistance=0.82, labeldistance=1.08,
        )
        for t in autotexts:
            t.set_fontsize(9)
        ax.set_title("新闻类别分布", fontsize=14, fontweight="bold", pad=16)
        fig.tight_layout()
        p = charts_dir / "category_distribution.png"
        fig.savefig(p, dpi=150, bbox_inches="tight")
        plt.close(fig)
        paths["category_distribution"] = p

    # ── 图表 2：来源分布水平条形图 ────────────────────────────────────────────
    src_dist = analysis["source_dist"]
    if src_dist:
        sorted_src = sorted(src_dist.items(), key=lambda x: x[1])
        labels = [s[0] for s in sorted_src]
        values = [s[1] for s in sorted_src]
        fig, ax = plt.subplots(figsize=(7, max(3, len(labels) * 0.7)))
        bars = ax.barh(labels, values, color=PALETTE[0], edgecolor="white")
        ax.bar_label(bars, padding=4, fontsize=10)
        ax.set_xlabel("新闻数量", fontsize=11)
        ax.set_title("新闻来源分布", fontsize=14, fontweight="bold", pad=12)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_xlim(0, max(values) * 1.2)
        fig.tight_layout()
        p = charts_dir / "source_distribution.png"
        fig.savefig(p, dpi=150, bbox_inches="tight")
        plt.close(fig)
        paths["source_distribution"] = p

    # ── 图表 3：重要性评分 Top 事件水平条形图 ─────────────────────────────────
    all_items_for_chart = sorted(
        analysis["top_events"], key=lambda x: x["importance_score"]
    )
    if all_items_for_chart:
        labels = [_truncate(i["title"]) for i in all_items_for_chart]
        scores = [i["importance_score"] for i in all_items_for_chart]
        norm_scores = [(s - 1) / 9 for s in scores]  # 归一化到 0-1 用于着色
        import matplotlib.cm as cm
        import matplotlib
        cmap = matplotlib.colormaps.get_cmap("Blues")
        colors = [cmap(0.4 + 0.5 * v) for v in norm_scores]
        fig, ax = plt.subplots(figsize=(9, max(3, len(labels) * 0.65)))
        bars = ax.barh(labels, scores, color=colors, edgecolor="white")
        ax.bar_label(bars, padding=4, fontsize=10)
        ax.set_xlabel("重要性评分（1-10）", fontsize=11)
        ax.set_title("重要性评分 Top 事件", fontsize=14, fontweight="bold", pad=12)
        ax.set_xlim(0, 11)
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        p = charts_dir / "top_importance.png"
        fig.savefig(p, dpi=150, bbox_inches="tight")
        plt.close(fig)
        paths["top_importance"] = p

    # ── 图表 4：事件时间线散点图 ──────────────────────────────────────────────
    timeline = analysis["timeline"]
    if timeline:
        import matplotlib.dates as mdates
        fig, ax = plt.subplots(figsize=(10, 4))
        xs = [t["dt"] for t in timeline]
        ys = [t["score"] for t in timeline]
        sc = ax.scatter(xs, ys, c=ys, cmap="Blues", vmin=1, vmax=10,
                        s=80, edgecolors="#4C72B0", linewidths=0.6, zorder=3)
        # 标注高分事件（score >= 8）
        for t in timeline:
            if t["score"] >= 8:
                ax.annotate(
                    _truncate(t["title"], 20),
                    xy=(t["dt"], t["score"]),
                    xytext=(6, 4), textcoords="offset points",
                    fontsize=7, color="#333333",
                )
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        fig.autofmt_xdate(rotation=30)
        ax.set_ylabel("重要性评分", fontsize=11)
        ax.set_title("事件时间线", fontsize=14, fontweight="bold", pad=12)
        ax.set_ylim(0, 11)
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        ax.spines[["top", "right"]].set_visible(False)
        plt.colorbar(sc, ax=ax, label="重要性评分")
        fig.tight_layout()
        p = charts_dir / "event_timeline.png"
        fig.savefig(p, dpi=150, bbox_inches="tight")
        plt.close(fig)
        paths["event_timeline"] = p

    return paths


# ══════════════════════════════════════════════════════════════════════════════
# Step 4 & 5: HTML 报告组装 + 趋势判断渲染
# ══════════════════════════════════════════════════════════════════════════════

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: "PingFang SC", "Helvetica Neue", Arial, sans-serif;
    background: #f5f6fa;
    color: #2d3436;
    line-height: 1.7;
}
.container { max-width: 960px; margin: 0 auto; padding: 32px 24px 64px; }
header {
    background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%);
    color: #fff;
    padding: 36px 32px 28px;
    border-radius: 12px;
    margin-bottom: 32px;
}
header h1 { font-size: 26px; font-weight: 700; margin-bottom: 8px; }
header .meta { font-size: 14px; opacity: 0.85; }
section {
    background: #fff;
    border-radius: 10px;
    padding: 28px 32px;
    margin-bottom: 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
h2 {
    font-size: 18px;
    font-weight: 700;
    color: #1a73e8;
    border-left: 4px solid #1a73e8;
    padding-left: 12px;
    margin-bottom: 20px;
}
h3 { font-size: 15px; font-weight: 600; margin: 16px 0 6px; color: #2d3436; }
.event-card {
    border: 1px solid #e8ecf0;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 14px;
    transition: box-shadow .2s;
}
.event-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.event-header { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 10px; }
.event-title { font-size: 15px; font-weight: 600; flex: 1; }
.event-title a { color: #2d3436; text-decoration: none; }
.event-title a:hover { color: #1a73e8; }
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
}
.badge-score-high   { background: #e8f5e9; color: #2e7d32; }
.badge-score-mid    { background: #fff3e0; color: #e65100; }
.badge-score-low    { background: #fce4ec; color: #c62828; }
.badge-source       { background: #e3f2fd; color: #1565c0; }
.badge-cat          { background: #f3e5f5; color: #6a1b9a; }
.badge-pos  { background: #e8f5e9; color: #2e7d32; }
.badge-neg  { background: #fce4ec; color: #c62828; }
.badge-neu  { background: #f5f5f5; color: #616161; }
.key-facts { list-style: disc; padding-left: 20px; font-size: 14px; color: #555; margin-top: 6px; }
.key-facts li { margin-bottom: 4px; }
.impact-block {
    background: #f8f9fa;
    border-left: 3px solid #1a73e8;
    padding: 10px 14px;
    border-radius: 0 6px 6px 0;
    font-size: 14px;
    margin: 8px 0;
    color: #444;
}
.risk-block {
    background: #fff8f0;
    border-left: 3px solid #f57c00;
    padding: 10px 14px;
    border-radius: 0 6px 6px 0;
    font-size: 14px;
    margin: 8px 0;
    color: #444;
}
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 640px) { .two-col { grid-template-columns: 1fr; } }
.trend-card {
    border: 1px solid #e8ecf0;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
}
.trend-label { font-size: 16px; font-weight: 700; color: #1a73e8; margin-bottom: 6px; }
.trend-summary { font-size: 14px; color: #555; margin-bottom: 8px; }
.trend-entities { font-size: 13px; color: #888; }
.charts-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media (max-width: 640px) { .charts-grid { grid-template-columns: 1fr; } }
.chart-item { text-align: center; }
.chart-item img { max-width: 100%; border-radius: 8px; border: 1px solid #e8ecf0; }
.chart-caption { font-size: 13px; color: #888; margin-top: 6px; }
.chart-full { grid-column: 1 / -1; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th { background: #f0f4ff; color: #1a73e8; padding: 10px 14px; text-align: left; }
td { padding: 9px 14px; border-bottom: 1px solid #f0f0f0; }
tr:last-child td { border-bottom: none; }
.pipeline-step {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 0;
    border-bottom: 1px dashed #e8ecf0;
    font-size: 14px;
}
.pipeline-step:last-child { border-bottom: none; }
.step-num {
    width: 28px; height: 28px;
    background: #1a73e8; color: #fff;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 700; flex-shrink: 0;
}
"""


def _score_badge(score: int) -> str:
    cls = "badge-score-high" if score >= 8 else ("badge-score-mid" if score >= 6 else "badge-score-low")
    return f'<span class="badge {cls}">评分 {score}</span>'


def _sentiment_badge(s: str) -> str:
    mapping = {"positive": ("badge-pos", "正面"), "negative": ("badge-neg", "负面"), "neutral": ("badge-neu", "中性")}
    cls, label = mapping.get(s, ("badge-neu", s))
    return f'<span class="badge {cls}">{label}</span>'


def _render_top_events(top_events: list[dict]) -> str:
    if not top_events:
        return "<p>暂无数据。</p>"
    parts = []
    for i, ev in enumerate(top_events, 1):
        facts_html = "".join(f"<li>{f}</li>" for f in ev.get("key_facts", []))
        parts.append(f"""
<div class="event-card">
  <div class="event-header">
    <div class="event-title">
      <span style="color:#1a73e8;font-weight:700;">#{i}</span>&nbsp;
      <a href="{ev['url']}" target="_blank" rel="noopener">{ev['title']}</a>
    </div>
    {_score_badge(ev['importance_score'])}
    {_sentiment_badge(ev['sentiment'])}
    <span class="badge badge-source">{ev['source']}</span>
    <span class="badge badge-cat">{ev['category']}</span>
  </div>
  <ul class="key-facts">{facts_html}</ul>
</div>""")
    return "\n".join(parts)


def _render_deep_summary(top_events: list[dict]) -> str:
    if not top_events:
        return "<p>暂无数据。</p>"
    parts = []
    for ev in top_events:
        parts.append(f"""
<div class="event-card">
  <h3><a href="{ev['url']}" target="_blank" rel="noopener">{ev['title']}</a></h3>
  <div class="impact-block"><strong>行业影响：</strong>{ev.get('impact', '—')}</div>
  <div class="impact-block"><strong>关键证据：</strong>{ev.get('evidence', '—')}</div>
  <div class="risk-block"><strong>风险/机会：</strong>{ev.get('risk_or_opportunity', '—')}</div>
</div>""")
    return "\n".join(parts)


def _render_trends(trends: dict) -> str:
    order = ["技术", "应用", "政策", "资本"]
    parts = []
    for label in order:
        t = trends.get(label)
        if not t:
            continue
        ents = "、".join(t["entities"]) if t["entities"] else "—"
        sent_bar = (
            f'<span class="badge badge-pos">正面 {t["positive"]}</span> '
            f'<span class="badge badge-neu">中性 {t["neutral"]}</span> '
            f'<span class="badge badge-neg">负面 {t["negative"]}</span>'
        )
        parts.append(f"""
<div class="trend-card">
  <div class="trend-label">{label}方向</div>
  <div class="trend-summary">{t['summary']}</div>
  <div style="margin-bottom:6px;">{sent_bar}</div>
  <div class="trend-entities">高频主体：{ents}</div>
</div>""")
    return "\n".join(parts)


def _render_risks_opportunities(risks: list[dict], opps: list[dict]) -> str:
    def card(item: dict) -> str:
        return f"""
<div class="event-card">
  <div class="event-header">
    <div class="event-title">
      <a href="{item['url']}" target="_blank" rel="noopener">{item['title']}</a>
    </div>
    {_sentiment_badge(item['sentiment'])}
  </div>
  <div class="risk-block">{item.get('risk_or_opportunity', '—')}</div>
</div>"""

    risk_html = "\n".join(card(i) for i in risks) if risks else "<p>暂无风险条目。</p>"
    opp_html  = "\n".join(card(i) for i in opps)  if opps  else "<p>暂无机会条目。</p>"
    return f"""
<div class="two-col">
  <div>
    <h3 style="color:#c62828;">⚠ 风险提示</h3>
    {risk_html}
  </div>
  <div>
    <h3 style="color:#2e7d32;">✦ 机会提示</h3>
    {opp_html}
  </div>
</div>"""


def _render_data_sources(source_dist: Counter, quality_dist: Counter, total: int) -> str:
    rows = "".join(
        f"<tr><td>{src}</td><td>{cnt}</td><td>{cnt/total:.0%}</td></tr>"
        for src, cnt in sorted(source_dist.items(), key=lambda x: -x[1])
    )
    q_rows = "".join(
        f"<tr><td>{q}</td><td>{c}</td></tr>"
        for q, c in quality_dist.items()
    )
    return f"""
<p>本次分析共收录 <strong>{total}</strong> 条新闻，来源如下：</p>
<table style="margin:16px 0;">
  <tr><th>来源</th><th>数量</th><th>占比</th></tr>
  {rows}
</table>
<h3>数据质量分布</h3>
<table style="margin:12px 0;">
  <tr><th>质量等级</th><th>数量</th></tr>
  {q_rows}
</table>
<p style="font-size:13px;color:#888;margin-top:8px;">
  注：<code>data_quality=low</code> 的条目（通常为 Hacker News 仅标题条目）仅参与分布统计，不进入深度分析。
</p>"""


def _render_pipeline() -> str:
    steps = [
        ("RSS 采集", "scripts/news_rss.py", "从机器之心、量子位、TechCrunch AI、The Verge AI、Hacker News AI 抓取 RSS，按 AI 关键词过滤，输出 data/news.json"),
        ("结构化抽取", "scripts/structure_news.py", "逐条调用 LLM 提取 category、event_type、sentiment、importance_score、entities、key_facts、impact、risk_or_opportunity 等字段，输出 data/structured_news.json"),
        ("统计分析", "reports/generate_report.py", "纯 Python 处理：按 importance_score 排序、Counter 聚合类别/来源/实体、规则引擎生成趋势语句、规则过滤风险/机会条目"),
        ("图表生成", "reports/generate_report.py", "matplotlib 生成类别分布饼图、来源分布条形图、重要性评分 Top 事件图、事件时间线散点图，保存为 PNG"),
        ("HTML 报告组装", "reports/generate_report.py", "Python f-string 模板将分析结果和图表引用组装为自包含 HTML 文件"),
    ]
    items = ""
    for i, (name, file, desc) in enumerate(steps, 1):
        items += f"""
<div class="pipeline-step">
  <div class="step-num">{i}</div>
  <div>
    <strong>{name}</strong>
    <span style="font-size:12px;color:#888;margin-left:8px;">{file}</span>
    <div style="color:#555;margin-top:2px;">{desc}</div>
  </div>
</div>"""
    return items


def _render_charts(chart_paths: dict[str, Path], charts_dir: Path) -> str:
    chart_meta = [
        ("category_distribution", "新闻类别分布"),
        ("source_distribution",   "新闻来源分布"),
        ("top_importance",        "重要性评分 Top 事件"),
    ]
    items = []
    for key, caption in chart_meta:
        if key not in chart_paths:
            continue
        rel = chart_paths[key].relative_to(charts_dir.parent)
        items.append(f"""
<div class="chart-item">
  <img src="{rel}" alt="{caption}">
  <div class="chart-caption">{caption}</div>
</div>""")
    return f'<div class="charts-grid">{"".join(items)}</div>'


def generate_html(
    analysis: dict,
    chart_paths: dict[str, Path],
    charts_dir: Path,
    output_path: Path,
    report_date: str,
) -> None:
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI 舆情分析日报 · {report_date}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="container">

<header>
  <h1>AI 舆情分析日报</h1>
  <div class="meta">
    {report_date} &nbsp;|&nbsp;
    共分析 {analysis['total']} 条新闻，覆盖 {len(analysis['source_dist'])} 个来源，
    高质量条目 {analysis['quality_total']} 条
  </div>
</header>

<section id="top-events">
  <h2>今日 AI 领域 Top 重要事件</h2>
  {_render_top_events(analysis['top_events'])}
</section>

<section id="deep-summary">
  <h2>重要事件深度总结</h2>
  {_render_deep_summary(analysis['top_events'])}
</section>

<section id="trends">
  <h2>趋势判断</h2>
  {_render_trends(analysis['trends'])}
</section>

<section id="risks-opportunities">
  <h2>风险与机会提示</h2>
  {_render_risks_opportunities(analysis['risks'], analysis['opportunities'])}
</section>

<section id="charts">
  <h2>数据可视化</h2>
  {_render_charts(chart_paths, charts_dir)}
</section>

<section id="data-sources">
  <h2>数据来源说明</h2>
  {_render_data_sources(analysis['source_dist'], analysis['quality_dist'], analysis['total'])}
</section>

</div>
</body>
</html>"""
    output_path.write_text(html, encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# 入口
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print("📥 加载数据…")
    all_items, quality_items = load_news(DATA_PATH)
    print(f"   全量 {len(all_items)} 条，高质量 {len(quality_items)} 条")

    print("📊 统计分析…")
    analysis = analyze(all_items, quality_items)
    print(f"   Top 事件 {len(analysis['top_events'])} 条，趋势方向 {len(analysis['trends'])} 个")

    print("🖼  生成图表…")
    chart_paths = generate_charts(analysis, CHARTS_DIR)
    print(f"   已生成 {len(chart_paths)} 张图表：{', '.join(chart_paths.keys())}")

    print("📝 组装 HTML 报告…")
    report_date = datetime.now().strftime("%Y-%m-%d")
    generate_html(analysis, chart_paths, CHARTS_DIR, REPORT_PATH, report_date)
    print(f"   报告已写入：{REPORT_PATH}")

    print("✅ 完成")


if __name__ == "__main__":
    main()
