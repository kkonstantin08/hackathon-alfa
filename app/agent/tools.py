"""Инструменты агента. Каждый возвращает list[Source] — они попадают в пул доказательств.

Реестр с обёрткой (идея tool hooks из CrewAI): проверка аргументов, лимит результатов, трасса.
source_id детерминирован и читаем: news:n001, bank:kr14#1, profile:key_rate, product:deposit, cp:U005.
"""

from __future__ import annotations

import inspect
import re
from collections.abc import Callable
from functools import lru_cache

import yaml

from app.bank_kb import kb
from app.config import settings
from app.llm import trace
from app.news import pipeline as news
from contracts.models import CompanyProfile, NewsItem, NewsTags, Source


class ToolContext:
    def __init__(self, profile: CompanyProfile, item: NewsItem, tags: NewsTags):
        self.profile, self.item, self.tags = profile, item, tags
        self.full_text: dict[str, str] = {}  # source_id → полный текст, для проверки чисел и цитат

    @property
    def news_factors(self) -> list[str]:
        """Факторы новости по убыванию силы."""
        return [f.factor for f in sorted(self.tags.factors, key=lambda f: -f.strength)]


def news_source(item: NewsItem, tags: NewsTags) -> Source:
    quote = tags.facts[0].quote if tags.facts else re.split(r"(?<=[.!?])\s+", item.text)[0]
    return Source(source_id=f"news:{item.news_id}", type="news", ref=item.url, title=item.title, quote=quote)


def search_bank(
    ctx: ToolContext, query: str = "", factors: list[str] | None = None, k: int = 3
) -> list[Source]:
    out = []
    for c in kb.search(query or ctx.item.title, factors or ctx.news_factors, k=k):
        sid = f"bank:{c.chunk_id}"
        ctx.full_text[sid] = c.text
        out.append(
            Source(
                source_id=sid,
                type="bank",
                ref=c.chunk_id,
                title=f"{c.doc_title}" + (f", с. {c.page}" if c.page else ""),
                quote=c.text[:400],
            )
        )
    return out


def related_news(
    ctx: ToolContext, factors: list[str] | None = None, days: int = 30, k: int = 3
) -> list[Source]:
    out = []
    for n in news.related(factors or ctx.news_factors, days=days, exclude=ctx.item.news_id, limit=k):
        sid = f"news:{n.news_id}"
        ctx.full_text[sid] = n.title + " " + n.text
        out.append(
            Source(
                source_id=sid,
                type="news",
                ref=n.url,
                title=n.title,
                quote=re.split(r"(?<=[.!?])\s+", n.text)[0],
            )
        )
    return out


def profile_facts(ctx: ToolContext, factors: list[str] | None = None) -> list[Source]:
    wanted = set(factors or ctx.news_factors)
    exps = [e for e in ctx.profile.exposures if e.factor in wanted]
    out = []
    for e in exps:
        ev = ", ".join(f"{x.field}={x.value}" for x in e.evidence)
        sid = f"profile:{e.factor}"
        ctx.full_text[sid] = f"{e.why} ({ev})"
        out.append(
            Source(source_id=sid, type="profile", ref=f"exposure:{e.factor}", title=e.factor, quote=e.why)
        )
    return out


def counterparty_exposure(ctx: ToolContext) -> list[Source]:
    out = []
    for cp in ctx.profile.counterparties[:3]:
        who = "поставщик" if cp.role == "supplier" else "покупатель"
        q = f"{who} {cp.company_id} (ОКВЭД {cp.okved_code or 'н/д'}) — {cp.share:.0%} оборота"
        sid = f"cp:{cp.company_id}"
        ctx.full_text[sid] = q
        out.append(
            Source(source_id=sid, type="profile", ref=f"counterparty:{cp.company_id}", title=who, quote=q)
        )
    return out


@lru_cache
def _products() -> list[dict]:
    return yaml.safe_load((settings().fixtures_dir / "bank_products.yaml").read_text(encoding="utf-8"))[
        "products"
    ]


def bank_products(ctx: ToolContext, factors: list[str] | None = None) -> list[Source]:
    wanted = set(factors or ctx.news_factors) & {e.factor for e in ctx.profile.exposures}
    out = []
    for p in _products():
        if wanted & set(p["factors"]):
            sid = f"product:{p['id']}"
            ctx.full_text[sid] = p["name"]
            out.append(Source(source_id=sid, type="product", ref=p["id"], title=p["name"], quote=p["name"]))
    return out[:3]


TOOLS: dict[str, Callable[..., list[Source]]] = {
    "search_bank": search_bank,
    "related_news": related_news,
    "profile_facts": profile_facts,
    "counterparty_exposure": counterparty_exposure,
    "bank_products": bank_products,
}


TOOL_DOCS = {
    "search_bank": "поиск по аналитическим материалам банка; query — что искать, factors — фильтр",
    "related_news": "предыдущие новости по тем же факторам за days дней — контекст события",
    "profile_facts": "почему факторы важны этой компании (продукты, ВЭД, отрасль) по её профилю",
    "counterparty_exposure": "крупные контрагенты компании по платежам и их отрасли",
    "bank_products": "продукты банка, которые помогают с этими факторами",
}


def describe() -> list[dict]:
    """Описание инструментов для промпта планировщика."""
    return [
        {"name": n, "args": [p for p in inspect.signature(f).parameters if p != "ctx"], "doc": TOOL_DOCS[n]}
        for n, f in TOOLS.items()
    ]


def run_tool(ctx: ToolContext, name: str, args: dict) -> list[Source]:
    """Хук до/после: отбрасываем неизвестные аргументы, ловим ошибки, пишем трассу."""
    fn = TOOLS[name]
    allowed = set(inspect.signature(fn).parameters) - {"ctx"}
    clean = {k: v for k, v in args.items() if k in allowed}
    dropped = sorted(set(args) - allowed)
    try:
        res = fn(ctx, **clean)
        trace.emit(
            f"tool.{name}",
            detail={"args": clean, "dropped_args": dropped, "n": len(res), "ids": [s.source_id for s in res]},
        )
        return res
    except Exception as e:  # инструмент не должен ронять карточку
        trace.emit(f"tool.{name}", ok=False, detail={"args": clean, "error": repr(e)[:300]})
        return []
