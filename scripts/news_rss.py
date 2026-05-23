#!/usr/bin/env python3
"""Fetch AI-related RSS news and maintain data/news.json."""

from __future__ import annotations

import html
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import struct_time

try:
    import feedparser
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: feedparser. Install it with `pip install feedparser`."
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NEWS_PATH = PROJECT_ROOT / "data" / "news.json"

MAX_ENTRIES_PER_SOURCE = 10
MAX_NEWS_ITEMS = 80
SUMMARY_MAX_LENGTH = 300
RECENT_DAYS = 3


@dataclass(frozen=True)
class RssSource:
    name: str
    url: str
    lang: str
    priority: int
    ai_only: bool


@dataclass
class SourceStats:
    fetched: int = 0
    accepted: int = 0


RSS_SOURCES = [
    RssSource(
        name="机器之心",
        url="https://www.jiqizhixin.com/feed",
        lang="zh",
        priority=1,
        ai_only=True,
    ),
    RssSource(
        name="量子位",
        url="https://www.qbitai.com/feed",
        lang="zh",
        priority=1,
        ai_only=True,
    ),
    RssSource(
        name="TechCrunch AI",
        url="https://techcrunch.com/category/artificial-intelligence/feed/",
        lang="en",
        priority=1,
        ai_only=True,
    ),
    RssSource(
        name="The Verge AI",
        url="https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        lang="en",
        priority=1,
        ai_only=True,
    ),
    RssSource(
        name="Hacker News AI",
        url=(
            "https://hnrss.org/newest?q=AI+OR+LLM+OR+GPT+OR+"
            "%22artificial+intelligence%22+OR+%22machine+learning%22&points=100"
        ),
        lang="en",
        priority=2,
        ai_only=True,
    ),
]


NON_AI_BLACKLIST = [
    "护发",
    "美妆",
    "护肤",
    "彩妆",
    "美容",
    "美甲",
    "美发",
    "汽车大灯",
    "车灯",
    "轮胎",
    "发动机",
    "变速箱",
    "美食",
    "菜谱",
    "烹饪",
    "餐厅",
    "外卖",
    "旅游",
    "酒店",
    "机票",
    "签证",
    "景点",
    "游戏攻略",
    "游戏评测",
    "手游",
    "网游",
    "电竞",
    "明星",
    "八卦",
    "综艺",
    "电影",
    "健康养生",
    "药品",
    "保健品",
    "中医",
    "感染",
    "肠胃",
    "肿瘤",
    "癌症",
    "疫苗",
    "房产",
    "装修",
    "家具",
    "家电",
    "A股",
    "B股",
    "港股",
    "美股",
    "股市",
    "涨跌",
    "沪指",
    "深成指",
    "创业板指",
    "三大指数",
    "中国移动",
    "中国联通",
    "工商银行",
    "建设银行",
    "理想汽车",
    "蔚来",
    "小鹏",
    "比亚迪",
    "特斯拉",
    "问界",
    "极氪",
]


ZH_AI_KEYWORDS = [
    "AI",
    "人工智能",
    "大模型",
    "LLM",
    "GPT",
    "ChatGPT",
    "Claude",
    "Gemini",
    "Llama",
    "DeepSeek",
    "Kimi",
    "豆包",
    "通义",
    "文心",
    "智谱",
    "百川",
    "MiniMax",
    "阶跃星辰",
    "深度学习",
    "机器学习",
    "神经网络",
    "自然语言",
    "NLP",
    "计算机视觉",
    "CV",
    "生成式",
    "AIGC",
    "AGI",
    "Transformer",
    "扩散模型",
    "智能体",
    "Agent",
    "Stable Diffusion",
    "Midjourney",
    "DALL-E",
    "Sora",
    "可灵",
    "seedance",
    "机器人",
    "具身智能",
    "自动驾驶",
    "世界模型",
    "vla模型",
    "语音识别",
    "TTS",
    "ASR",
    "英伟达",
    "NVIDIA",
    "GPU",
    "算力",
    "芯片",
    "H100",
    "A100",
    "寒武纪",
    "摩尔线程",
    "砺算科技",
    "沐曦科技",
    "光芯片",
    "OpenAI",
    "Anthropic",
    "Google AI",
    "Meta AI",
    "微软 AI",
    "百度 AI",
    "阿里 AI",
    "腾讯 AI",
    "字节 AI",
    "华为 AI",
    "美团ai",
    "快手ai",
    "月之暗面",
    "minimax",
    "科大讯飞",
    "商汤",
    "旷视",
]


EN_AI_KEYWORDS = [
    "AI",
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "LLM",
    "GPT",
    "ChatGPT",
    "Claude",
    "Gemini",
    "Llama",
    "transformer",
    "diffusion",
    "generative",
    "AIGC",
    "AGI",
    "agent",
    "neural network",
    "NLP",
    "OpenAI",
    "Anthropic",
    "Google AI",
    "Meta AI",
    "Microsoft AI",
    "NVIDIA",
    "GPU",
    "inference",
    "training",
    "fine-tuning",
    "RLHF",
    "Stable Diffusion",
    "Midjourney",
    "DALL-E",
    "Sora",
    "Whisper",
]


HTML_TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def clean_text(value: object, max_len: int | None = None) -> str:
    if value is None:
        return ""
    text = str(value)
    if not text:
        return ""
    text = HTML_TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = SPACE_RE.sub(" ", text).strip()
    if max_len is not None and len(text) > max_len:
        text = text[:max_len].rstrip()
    return text


def contains_keyword(text: str, keywords: list[str]) -> bool:
    normalized_text = text.upper()
    for keyword in keywords:
        normalized_keyword = keyword.upper()
        if re.fullmatch(r"[A-Z0-9][A-Z0-9 ._+-]*", normalized_keyword):
            pattern = (
                r"(?<![A-Z0-9])"
                + re.escape(normalized_keyword)
                + r"(?![A-Z0-9])"
            )
            if re.search(pattern, normalized_text):
                return True
        elif normalized_keyword in normalized_text:
            return True
    return False


def is_ai_related(title: str, summary: str, lang: str, ai_only: bool) -> bool:
    del ai_only
    combined = f"{title} {summary}".strip()
    if not combined:
        return False
    if contains_keyword(combined, NON_AI_BLACKLIST):
        return False
    if lang == "zh":
        return contains_keyword(combined, ZH_AI_KEYWORDS)
    if lang == "en":
        return contains_keyword(combined, EN_AI_KEYWORDS)
    return contains_keyword(combined, ZH_AI_KEYWORDS + EN_AI_KEYWORDS)


def parse_published(entry: dict) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not isinstance(parsed, struct_time):
        return None
    return datetime(*parsed[:6], tzinfo=UTC)


def is_recent(published: datetime | None, now: datetime) -> bool:
    if published is None:
        return True
    cutoff = now - timedelta(days=RECENT_DAYS)
    return published >= cutoff


def generate_id(url: str) -> str:
    return hashlib.md5(url.encode("utf-8")).hexdigest()[:12]


def entry_to_news(source: RssSource, entry: dict, now: datetime) -> dict | None:
    url = clean_text(entry.get("link"))
    if not url:
        return None

    title = clean_text(entry.get("title"))
    summary = clean_text(
        entry.get("summary") or entry.get("description"), max_len=SUMMARY_MAX_LENGTH
    )
    published_dt = parse_published(entry)

    if not is_recent(published_dt, now):
        return None
    if not is_ai_related(title, summary, source.lang, source.ai_only):
        return None

    return {
        "id": generate_id(url),
        "title": title,
        "url": url,
        "source": source.name,
        "lang": source.lang,
        "priority": source.priority,
        "published": published_dt.isoformat() if published_dt else None,
        "summary": summary,
        "collected_at": now.isoformat(),
    }


def load_existing_news() -> list[dict]:
    if not NEWS_PATH.exists():
        return []
    try:
        data = json.loads(NEWS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def parse_iso_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def normalize_existing_news(item: dict, now: datetime) -> dict | None:
    url = clean_text(item.get("url"))
    if not url:
        return None

    lang = clean_text(item.get("lang")) or "en"
    title = clean_text(item.get("title"))
    summary = clean_text(item.get("summary"), max_len=SUMMARY_MAX_LENGTH)
    published_dt = parse_iso_datetime(item.get("published"))

    if not is_recent(published_dt, now):
        return None
    if not is_ai_related(title, summary, lang, bool(item.get("ai_only", True))):
        return None

    priority = item.get("priority", 1)
    if not isinstance(priority, int):
        priority = 1

    return {
        "id": clean_text(item.get("id")) or generate_id(url),
        "title": title,
        "url": url,
        "source": clean_text(item.get("source")),
        "lang": lang,
        "priority": priority,
        "published": published_dt.isoformat() if published_dt else None,
        "summary": summary,
        "collected_at": clean_text(item.get("collected_at")) or now.isoformat(),
    }


def sort_key(item: dict) -> tuple[int, str]:
    published = item.get("published")
    return (1 if published else 0, published or "")


def merge_news(existing: list[dict], fresh: list[dict], now: datetime) -> list[dict]:
    normalized = []
    for item in existing:
        cleaned = normalize_existing_news(item, now)
        if cleaned:
            normalized.append(cleaned)
    normalized.extend(fresh)

    deduped: dict[str, dict] = {}
    for item in normalized:
        news_id = item.get("id")
        if isinstance(news_id, str) and news_id:
            deduped[news_id] = item

    sorted_items = sorted(deduped.values(), key=sort_key, reverse=True)
    return sorted_items[:MAX_NEWS_ITEMS]


def save_news(items: list[dict]) -> None:
    NEWS_PATH.parent.mkdir(parents=True, exist_ok=True)
    NEWS_PATH.write_text(
        json.dumps(items, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def fetch_feed_entries(source: RssSource) -> list[dict]:
    feed = feedparser.parse(source.url)
    entries = list(feed.entries[:MAX_ENTRIES_PER_SOURCE])
    return entries


def collect_entries() -> tuple[list[tuple[RssSource, dict]], dict[str, SourceStats]]:
    collected: list[tuple[RssSource, dict]] = []
    stats: dict[str, SourceStats] = {}
    for source in RSS_SOURCES:
        entries = fetch_feed_entries(source)
        stats[source.name] = SourceStats(fetched=len(entries), accepted=0)
        for entry in entries:
            collected.append((source, entry))
    return collected, stats


def main() -> None:
    now = datetime.now(UTC)
    fresh = []
    print(f"Fetching {len(RSS_SOURCES)} RSS sources...")
    collected, stats = collect_entries()
    for source, entry in collected:
        news = entry_to_news(source, entry, now)
        if news:
            fresh.append(news)
            stats[source.name].accepted += 1

    existing = load_existing_news()
    final_items = merge_news(existing, fresh, now)
    save_news(final_items)

    for source in RSS_SOURCES:
        source_stats = stats[source.name]
        print(
            f"{source.name}: fetched {source_stats.fetched}, "
            f"accepted {source_stats.accepted}"
        )
    print(f"Merged: old {len(existing)} + new {len(fresh)} => final {len(final_items)}")
    print(f"Saved to {NEWS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
