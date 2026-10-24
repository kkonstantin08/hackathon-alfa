"""M4 ranking: персональная лента по формуле. Без LLM.

score(c, n) = (Σ_f exposure(c,f) · strength(n,f) · idf(f) + бонусы) · exp(-age / tau)

idf(f) обязателен: фактор, который есть почти у всех (ставка), иначе забьёт всю ленту.

Публичное API:
    feed(company_id, k=20) -> list[RankedNews]
"""

from __future__ import annotations

import math
import os
from datetime import datetime

from app.news import pipeline as news
from app.profiles import build as profiles
from contracts.models import CompanyProfile, NewsItem, NewsTags, RankedNews, Reason

LEVEL_W = {"low": 0.5, "medium": 1.0, "high": 1.5}
TAU_DAYS = float(os.environ.get("FEED_TAU_DAYS", "14"))  # подобрать на реальном корпусе
# Отраслевая новость не про отрасль компании: вклад её факторов уменьшаем (пример: пошлина на зерно
# и металлург с ВЭД — фактор «таможня» совпал, но событие не его).
OFF_SECTOR_DAMP = 0.4
BONUS_REGION = 0.3
BONUS_COUNTRY = 0.5
BONUS_SECTOR = 0.5


def factor_idf(all_profiles: list[CompanyProfile]) -> dict[str, float]:
    n = len(all_profiles)
    df: dict[str, int] = {}
    for p in all_profiles:
        for e in p.exposures:
            df[e.factor] = df.get(e.factor, 0) + 1
    return {f: math.log((n + 1) / (c + 1)) + 1.0 for f, c in df.items()}


def _now(items: list[NewsItem]) -> datetime:
    from app.config import settings

    s = settings().now
    return datetime.fromisoformat(s) if s else max(i.published_at for i in items)


def score_one(
    p: CompanyProfile, n: NewsItem, t: NewsTags, idf: dict[str, float], now: datetime
) -> tuple[float, list[Reason]]:
    exp = {e.factor: e for e in p.exposures}
    reasons: list[Reason] = []
    base = 0.0
    cp_codes = [c.okved_code or "" for c in p.counterparties if c.share >= 0.2]
    in_sector = not t.sectors or any(
        code.startswith(s) for s in t.sectors for code in [p.okved_code, *cp_codes]
    )
    for ft in t.factors:
        e = exp.get(ft.factor)
        if not e:
            continue
        c = (
            LEVEL_W[e.level]
            * (ft.strength / 3)
            * idf.get(ft.factor, 1.0)
            * (1.0 if in_sector else OFF_SECTOR_DAMP)
        )
        base += c
        arrow = {"up": "↑", "down": "↓"}.get(ft.direction, "")
        reasons.append(
            Reason(factor=ft.factor, text=f"{ft.factor}{arrow} — {e.why}", contribution=round(c, 3))
        )
    if p.region and p.region in t.regions:
        base += BONUS_REGION
        reasons.append(Reason(text=f"ваш регион: {p.region}", contribution=BONUS_REGION))
    if p.fts_country and p.fts_country in t.countries:
        base += BONUS_COUNTRY
        reasons.append(Reason(text=f"страна ВЭД: {p.fts_country}", contribution=BONUS_COUNTRY))
    if any(p.okved_code.startswith(s) for s in t.sectors if s):
        base += BONUS_SECTOR
        reasons.append(Reason(text=f"ваша отрасль: {p.okved_name}", contribution=BONUS_SECTOR))
    age = max((now - n.published_at).total_seconds() / 86400, 0)
    reasons.sort(key=lambda r: -r.contribution)
    return base * math.exp(-age / TAU_DAYS), reasons[:3]


def feed(company_id: str, k: int = 20) -> list[RankedNews]:
    p = profiles.get(company_id)
    if p is None:
        raise KeyError(company_id)
    items = news.all_news()
    if not items:
        return []
    tags = news.all_tags()
    idf = factor_idf(profiles.all_profiles())
    now = _now(items)
    best_by_cluster: dict[str, RankedNews] = {}
    for n in items:
        t = tags.get(n.news_id)
        if not t:
            continue
        s, reasons = score_one(p, n, t, idf, now)
        if s <= 0:
            continue
        r = RankedNews(
            company_id=company_id,
            news_id=n.news_id,
            title=n.title,
            source=n.source,
            published_at=n.published_at,
            score=round(s, 4),
            reasons=reasons,
        )
        cl = t.cluster_id or n.news_id
        if cl not in best_by_cluster or best_by_cluster[cl].score < r.score:
            best_by_cluster[cl] = r
    return sorted(best_by_cluster.values(), key=lambda r: -r.score)[:k]
