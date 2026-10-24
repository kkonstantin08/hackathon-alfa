"""Чат по карточке. Те же инструменты, контекст = карточка + профиль + поиск по материалам банка."""

from __future__ import annotations

import os

from app import store
from app.agent import prompts, tools
from app.llm import trace
from app.llm.gateway import call_structured
from app.news import pipeline as news
from app.profiles import build as profiles
from contracts.models import AnalysisCard, ChatAnswer

CHAT_MODEL = os.environ.get("CHAT_MODEL", "qwen")


def chat(card_id: str, message: str, history: list[dict] | None = None) -> tuple[ChatAnswer, str]:
    card = store.get("cards", card_id, AnalysisCard)
    if card is None:
        raise KeyError(card_id)
    ctx_tools = tools.ToolContext(
        profiles.get(card.company_id), news.get(card.news_id), news.tags(card.news_id)
    )
    tid = trace.new_trace("chat")
    extra = tools.run_tool(ctx_tools, "search_bank", {"query": message, "k": 3})
    allowed = {s.source_id for s in card.sources} | {s.source_id for s in extra}

    def sources_known(a: ChatAnswer) -> list[str]:
        return [
            f"неизвестные source_ids {c.source_ids}" for c in a.claims if not set(c.source_ids) <= allowed
        ]

    ctx = {
        "card": card.model_dump(mode="json"),
        "extra_sources": [s.model_dump() for s in extra],
        "history": (history or [])[-6:],
        "question": message,
    }
    ans = call_structured(
        CHAT_MODEL,
        prompts.msgs(prompts.CHAT, ctx),
        ChatAnswer,
        validators=[sources_known],
        step="agent.chat",
        temperature=0.2,
    )
    return ans, tid
