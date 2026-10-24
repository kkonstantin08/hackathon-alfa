"""M2 news: корпус → NewsItem → NewsTags (Gemma) → кластеры дублей.

Публичное API:
    load(jsonl) -> list[NewsItem]
    tag(item) -> NewsTags                       # LLM (gemma), кэшируется шлюзом
    dedup(items, tags) -> dict[news_id, cluster_id]
    get(news_id), tags(news_id), all_news(), all_tags()
    related(factors, days=30, exclude=None, limit=5) -> list[NewsItem]
"""

from __future__ import annotations

import json
import re
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

import yaml

from app import store
from app.config import settings
from app.llm.gateway import call_structured, context_block
from contracts.models import NewsItem, NewsTags, NewsTagsLLM, factor_ids

TAG_PROMPT = """Ты аналитик новостей для руководителей бизнеса.
Разметь новость факторами влияния на бизнес. Используй ТОЛЬКО id факторов из списка в контексте.
- direction: up — фактор растёт/усиливается, down — снижается/ослабевает, neutral, unclear.
- strength: 3 — новость прямо про этот фактор, 2 — заметное влияние, 1 — фон.
- facts: 1–3 ключевых факта, у каждого дословная цитата из текста.
- sectors: коды ОКВЭД (2–4 знака) затронутых отраслей, если очевидны.
Не придумывай факты, которых нет в тексте."""


@lru_cache
def factor_dicts() -> list[dict]:
    return yaml.safe_load((settings().contracts_dir / "factors.yaml").read_text(encoding="utf-8"))["factors"]


def load(path: Path) -> list[NewsItem]:
    with open(path, encoding="utf-8") as f:
        return [NewsItem.model_validate(json.loads(line)) for line in f if line.strip()]


def _quotes_in_text(item: NewsItem):
    def check(obj: NewsTagsLLM) -> list[str]:
        body = re.sub(r"\s+", " ", item.title + " " + item.text).lower()
        return [
            f"цитата не найдена в тексте: «{f.quote[:80]}»"
            for f in obj.facts
            if re.sub(r"\s+", " ", f.quote).lower() not in body
        ]

    return check


def tag(item: NewsItem, known_regions: list[str] | None = None) -> NewsTags:
    ctx = {
        "title": item.title,
        "text": item.text[:6000],
        "factors": [
            {
                "id": f["id"],
                "name": f["name"],
                "hint": f.get("hint", ""),
                "keywords": f.get("keywords", []),
                "sectors": f.get("sectors", []),
            }
            for f in factor_dicts()
        ],
        "known_regions": known_regions or [],
    }
    out = call_structured(
        "gemma",
        [{"role": "system", "content": TAG_PROMPT}, {"role": "user", "content": context_block(ctx)}],
        NewsTagsLLM,
        validators=[_quotes_in_text(item)],
        step="news.tag",
    )
    out.factors = [f for f in out.factors if f.factor in factor_ids()]
    return NewsTags(
        news_id=item.news_id,
        tagger=settings().llm_mode,
        **out.model_dump(exclude={"factors"}),
        factors=out.factors,
    )


def _tokens(s: str) -> set[str]:
    from app.bank_kb.kb import _stem

    return {_stem(w) for w in re.findall(r"\w+", s.lower()) if len(w) > 3}


def dedup(
    items: list[NewsItem], tags: dict[str, NewsTags], threshold: float = 0.3, window_days: int = 2
) -> dict[str, str]:
    """Кластеры одного события. Без эмбеддингов: коэффициент перекрытия основ слов (заголовок + начало
    текста) + совпадение главного фактора + окно по дате.

    ВНИМАНИЕ: лексический дедуп слабый. На fixtures пересказ одного события даёт 0.31, а две разные
    новости про металлы — 0.29. Держится только на окне по дате и главном факторе.
    Это главный аргумент за эмбеддинги: EMBEDDINGS=on → косинус (TODO B)."""
    items = sorted(items, key=lambda x: x.published_at)
    cluster: dict[str, str] = {}
    toks = {i.news_id: _tokens(i.title + " " + i.text[:300]) for i in items}

    def main_factor(nid: str) -> str | None:
        fs = tags.get(nid).factors if tags.get(nid) else []
        return max(fs, key=lambda f: f.strength).factor if fs else None

    for i, a in enumerate(items):
        if a.news_id in cluster:
            continue
        cluster[a.news_id] = a.news_id
        for b in items[i + 1 :]:
            if b.news_id in cluster or b.published_at - a.published_at > timedelta(days=window_days):
                continue
            inter = len(toks[a.news_id] & toks[b.news_id])
            smaller = min(len(toks[a.news_id]), len(toks[b.news_id])) or 1
            if inter / smaller >= threshold and main_factor(a.news_id) == main_factor(b.news_id):
                cluster[b.news_id] = a.news_id
    return cluster


def save(items: list[NewsItem], tags: list[NewsTags]) -> None:
    store.clear("news")
    store.clear("news_tags")
    store.put_many("news", [(i.news_id, i) for i in items])
    store.put_many("news_tags", [(t.news_id, t) for t in tags])


def get(news_id: str) -> NewsItem | None:
    return store.get("news", news_id, NewsItem)


def tags(news_id: str) -> NewsTags | None:
    return store.get("news_tags", news_id, NewsTags)


def all_news() -> list[NewsItem]:
    return store.all_("news", NewsItem)


def all_tags() -> dict[str, NewsTags]:
    return {t.news_id: t for t in store.all_("news_tags", NewsTags)}


def related(factors: list[str], days: int = 30, exclude: str | None = None, limit: int = 5) -> list[NewsItem]:
    """Предыдущие новости по тем же факторам. Эмбеддинги — второй слой, когда будут (TODO B)."""
    tg = all_tags()
    anchor = get(exclude) if exclude else None
    out = []
    for n in all_news():
        if n.news_id == exclude:
            continue
        if anchor and not (timedelta(0) <= anchor.published_at - n.published_at <= timedelta(days=days)):
            continue
        t = tg.get(n.news_id)
        overlap = len({f.factor for f in t.factors} & set(factors)) if t else 0
        if overlap:
            out.append((overlap, n.published_at, n))
    out.sort(key=lambda x: (-x[0], -x[1].timestamp()))
    return [n for _, _, n in out[:limit]]
