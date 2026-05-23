#!/usr/bin/env python3
"""Structure raw AI news items from data/news.json.

The extractor intentionally processes one item at a time. This keeps facts from
different articles isolated and makes low-quality inputs visible through
data_quality and needs_review.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NEWS_PATH = PROJECT_ROOT / "data" / "news.json"
STRUCTURED_NEWS_PATH = PROJECT_ROOT / "data" / "structured_news.json"

BATCH_SIZE = 1

CATEGORIES = {"模型发布", "Agent", "算力", "应用", "政策", "资本", "安全", "其他"}
EVENT_TYPES = {"产品发布", "研究进展", "融资并购", "监管政策", "安全风险", "行业观点", "其他"}
SENTIMENTS = {"positive", "neutral", "negative"}
DATA_QUALITY_VALUES = {"high", "medium", "low"}

DEFAULT_IMPORTANCE_SCORE = 5

HN_METADATA_PATTERN = re.compile(
    r"(Article URL:|Comments URL:|Points:\s*\d+|# Comments:\s*\d+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RawNewsItem:
    id: str
    title: str
    url: str
    source: str
    published: str
    summary: str


@dataclass
class StructuredNewsItem:
    id: str
    title: str
    url: str
    source: str
    published: str
    category: str
    entities: list[str]
    event_type: str
    importance_score: int
    sentiment: str
    key_facts: list[str]
    impact: str
    risk_or_opportunity: str
    evidence: str
    data_quality: str
    needs_review: bool


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    lower_text = text.lower()
    return any(keyword.lower() in lower_text for keyword in keywords)


def load_raw_news(path: Path = NEWS_PATH) -> list[RawNewsItem]:
    items = json.loads(path.read_text(encoding="utf-8"))
    return [
        RawNewsItem(
            id=str(item.get("id", "")),
            title=normalize_space(str(item.get("title", ""))),
            url=normalize_space(str(item.get("url", ""))),
            source=normalize_space(str(item.get("source", ""))),
            published=normalize_space(str(item.get("published", ""))),
            summary=normalize_space(str(item.get("summary", ""))),
        )
        for item in items
    ]


def is_hn_metadata_summary(summary: str) -> bool:
    return bool(HN_METADATA_PATTERN.search(summary))


def is_effective_summary(summary: str) -> bool:
    return bool(summary) and not is_hn_metadata_summary(summary)


def inference_text(item: RawNewsItem) -> str:
    if is_effective_summary(item.summary):
        return f"{item.title} {item.summary}"
    return item.title


def infer_data_quality(item: RawNewsItem) -> tuple[str, bool]:
    if is_hn_metadata_summary(item.summary):
        return "low", True

    summary_length = len(item.summary)
    if summary_length >= 120:
        return "high", False
    if summary_length >= 40:
        return "medium", True
    if item.title and summary_length > 0:
        return "medium", True
    return "low", True


def infer_category(item: RawNewsItem) -> str:
    text = inference_text(item)

    if contains_any(text, ("executive order", "regulation", "regulatory", "policy", "trial", "government", "监管", "政策")):
        return "政策"
    if contains_any(text, ("funding", "financing", "arr", "revenue", "vc", "investor", "acquisition", "融资", "并购", "资本", "估值")):
        return "资本"
    if contains_any(text, ("security", "safety", "risk", "dead pilots", "cockpit", "accident", "安全", "事故", "风险")):
        return "安全"
    if contains_any(text, ("gpu", "chip", "nvidia", "samsung", "h100", "算力", "芯片", "半导体")):
        return "算力"
    if contains_any(text, ("agent", "agents", "智能体")):
        return "Agent"
    if contains_any(text, ("model", "llm", "benchmark", "gpt", "deepseek code", "grok", "模型", "大模型")):
        return "模型发布"
    if contains_any(
        text,
        (
            "search",
            "spotify",
            "remix",
            "cover",
            "glasses",
            "guitar pedal",
            "podcast",
            "app",
            "tool",
            "google",
            "应用",
            "产品",
        ),
    ):
        return "应用"
    return "其他"


def infer_event_type(item: RawNewsItem) -> str:
    text = inference_text(item)

    if contains_any(text, ("executive order", "regulation", "regulatory", "policy", "trial", "监管", "政策")):
        return "监管政策"
    if contains_any(text, ("funding", "financing", "arr", "revenue", "vc", "investor", "acquisition", "融资", "并购", "估值")):
        return "融资并购"
    if contains_any(text, ("security", "safety", "risk", "blocked", "accident", "dead pilots", "broken", "安全", "事故", "风险")):
        return "安全风险"
    if contains_any(text, ("launch", "release", "announced", "new app", "tool", "deal allowing", "generated remixes", "发布", "上线", "来了")):
        return "产品发布"
    if contains_any(text, ("benchmark", "research", "study", "database", "open-source", "研究", "基准")):
        return "研究进展"
    if contains_any(text, ("opinion", "prepared", "profitable", "will lose", "not convinced", "worth trying", "观点", "评论")):
        return "行业观点"
    return "其他"


KNOWN_ENTITIES = (
    "OpenAI",
    "NVIDIA",
    "Google",
    "Google Search",
    "Google AI",
    "Gemini",
    "Microsoft",
    "Spotify",
    "Universal Music Group",
    "UMG",
    "YouTube",
    "TikTok",
    "Instagram",
    "Elon Musk",
    "Sam Altman",
    "Grok",
    "DeepSeek",
    "DeepSeek Code",
    "Trump",
    "NTSB",
    "Hacker News",
    "Samsung",
    "Steve Wozniak",
    "OpenSCAD",
    "Antigravity 2.0",
    "智谱",
    "崔添翼",
    "深圳",
)


def extract_entities(item: RawNewsItem) -> list[str]:
    text = inference_text(item)
    entities: list[str] = []

    for entity in KNOWN_ENTITIES:
        if entity.lower() in text.lower() and entity not in entities:
            entities.append(entity)

    acronym_pattern = re.compile(r"\b[A-Z][A-Z0-9]{1,}\b")
    for match in acronym_pattern.findall(text):
        if match not in {"AI", "URL"} and match not in entities:
            entities.append(match)

    return entities[:8]


def infer_sentiment(item: RawNewsItem, event_type: str) -> str:
    text = inference_text(item)

    if contains_any(
        text,
        (
            "broken",
            "blocked",
            "risk",
            "accident",
            "dead pilots",
            "expensive",
            "cost",
            "lose",
            "inflated",
            "not profitable",
            "humiliating",
            "isn't prepared",
            "not very good",
            "不确定",
            "风险",
        ),
    ):
        return "negative"
    if event_type in {"产品发布", "研究进展", "融资并购"} and contains_any(
        text,
        ("launch", "release", "deal", "open-source", "funding", "bonus", "soar", "融资", "拿下", "最快"),
    ):
        return "positive"
    if event_type in {"安全风险", "监管政策", "行业观点"}:
        return "neutral"
    return "neutral"


def extract_key_facts(item: RawNewsItem, data_quality: str) -> list[str]:
    facts = [f"The title reports: {item.title}"]

    if is_effective_summary(item.summary):
        sentences = re.split(r"(?<=[.!?。！？])\s+", item.summary)
        for sentence in sentences:
            sentence = normalize_space(sentence)
            if sentence and sentence not in facts:
                facts.append(sentence)
            if len(facts) >= 3:
                break

    if data_quality == "low":
        return facts[:1]
    return facts[:3]


def build_evidence(item: RawNewsItem) -> str:
    if is_effective_summary(item.summary):
        first_sentence = re.split(r"(?<=[.!?。！？])\s+", item.summary)[0]
        return normalize_space(first_sentence) or item.title
    return item.title


def infer_impact(category: str, event_type: str, data_quality: str) -> str:
    if data_quality == "low":
        return "The available metadata is limited, so the industry impact should be treated as a signal for follow-up rather than a firm conclusion."
    if category == "政策" or event_type == "监管政策":
        return "This may affect how AI companies evaluate compliance, product release timing, and policy uncertainty."
    if category == "资本" or event_type == "融资并购":
        return "This reflects investor and market attention around AI business models, growth quality, and commercialization pressure."
    if category == "安全" or event_type == "安全风险":
        return "This highlights safety, misuse, or reliability concerns that may influence trust in AI systems."
    if category == "算力":
        return "This points to continued dependence on chips, compute infrastructure, and hardware economics in AI growth."
    if category in {"模型发布", "Agent"} or event_type in {"产品发布", "研究进展"}:
        return "This may influence AI product capabilities, developer adoption, and competitive positioning."
    if category == "应用":
        return "This shows how AI is moving into user-facing products and changing expectations for software experiences."
    return "This provides a directional signal about current AI industry discussion, but the broader impact needs more context."


def infer_risk_or_opportunity(category: str, event_type: str, sentiment: str, data_quality: str) -> str:
    if data_quality == "low":
        return "The main risk is over-interpreting a low-context item; the opportunity is to use it as a candidate for manual review or deeper source extraction."
    if sentiment == "negative":
        return "The item points to reputational, safety, cost, policy, or adoption risks that should be handled cautiously in downstream analysis."
    if category == "资本":
        return "The opportunity is market validation for AI businesses, while the risk is that growth or revenue quality may be overstated."
    if category == "政策":
        return "The opportunity is clearer operating guidance if policy stabilizes, while the risk is continued regulatory uncertainty."
    if event_type == "产品发布":
        return "The opportunity is new user adoption or product differentiation, while the risk is execution quality and user trust."
    return "The opportunity is stronger signal discovery for AI trends, while the risk depends on whether follow-up sources confirm the details."


def infer_importance_score(item: RawNewsItem, category: str, event_type: str, data_quality: str) -> int:
    score = 5
    text = inference_text(item)

    if item.source in {"TechCrunch AI", "The Verge AI", "量子位"}:
        score += 1
    if category in {"政策", "资本", "安全", "算力"}:
        score += 1
    if event_type in {"监管政策", "融资并购", "安全风险"}:
        score += 1
    if contains_any(text, ("OpenAI", "Google", "NVIDIA", "Microsoft", "DeepSeek", "Samsung", "Trump", "Spotify")):
        score += 1
    if is_hn_metadata_summary(item.summary):
        points_match = re.search(r"Points:\s*(\d+)", item.summary)
        if points_match and int(points_match.group(1)) >= 200:
            score += 1

    if data_quality == "low":
        score = min(score, 6)
    elif data_quality == "medium":
        score = min(score, 7)

    return max(1, min(10, score))


def structure_item(item: RawNewsItem) -> StructuredNewsItem:
    data_quality, needs_review = infer_data_quality(item)
    category = infer_category(item)
    event_type = infer_event_type(item)
    sentiment = infer_sentiment(item, event_type)

    structured = StructuredNewsItem(
        id=item.id,
        title=item.title,
        url=item.url,
        source=item.source,
        published=item.published,
        category=category,
        entities=extract_entities(item),
        event_type=event_type,
        importance_score=infer_importance_score(item, category, event_type, data_quality),
        sentiment=sentiment,
        key_facts=extract_key_facts(item, data_quality),
        impact=infer_impact(category, event_type, data_quality),
        risk_or_opportunity=infer_risk_or_opportunity(category, event_type, sentiment, data_quality),
        evidence=build_evidence(item),
        data_quality=data_quality,
        needs_review=needs_review,
    )
    return validate_structured_item(structured)


def validate_structured_item(item: StructuredNewsItem) -> StructuredNewsItem:
    if item.category not in CATEGORIES:
        item.category = "其他"
        item.needs_review = True
    if item.event_type not in EVENT_TYPES:
        item.event_type = "其他"
        item.needs_review = True
    if item.sentiment not in SENTIMENTS:
        item.sentiment = "neutral"
        item.needs_review = True
    if item.data_quality not in DATA_QUALITY_VALUES:
        item.data_quality = "low"
        item.needs_review = True
    if not isinstance(item.entities, list):
        item.entities = []
        item.needs_review = True
    if not item.key_facts:
        item.key_facts = [f"The title reports: {item.title}" if item.title else "No source fact was available."]
        item.needs_review = True
    try:
        item.importance_score = int(item.importance_score)
    except (TypeError, ValueError):
        item.importance_score = DEFAULT_IMPORTANCE_SCORE
        item.needs_review = True
    item.importance_score = max(1, min(10, item.importance_score))

    for field_name in ("id", "title", "url", "source", "published", "impact", "risk_or_opportunity", "evidence"):
        if not getattr(item, field_name):
            setattr(item, field_name, "")
            item.needs_review = True

    return item


def structure_news(items: list[RawNewsItem]) -> list[StructuredNewsItem]:
    structured_items: list[StructuredNewsItem] = []
    for index in range(0, len(items), BATCH_SIZE):
        batch = items[index : index + BATCH_SIZE]
        for item in batch:
            structured_items.append(structure_item(item))
    return structured_items


def write_structured_news(items: list[StructuredNewsItem], path: Path = STRUCTURED_NEWS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: list[dict[str, Any]] = [asdict(item) for item in items]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    raw_items = load_raw_news()
    structured_items = structure_news(raw_items)
    write_structured_news(structured_items)

    needs_review_count = sum(1 for item in structured_items if item.needs_review)
    quality_counts = {quality: sum(1 for item in structured_items if item.data_quality == quality) for quality in sorted(DATA_QUALITY_VALUES)}
    print(f"Structured {len(structured_items)} news items -> {STRUCTURED_NEWS_PATH.relative_to(PROJECT_ROOT)}")
    print(f"BATCH_SIZE={BATCH_SIZE}; needs_review={needs_review_count}")
    print(
        "data_quality="
        + ", ".join(f"{quality}:{count}" for quality, count in quality_counts.items())
    )


if __name__ == "__main__":
    main()
