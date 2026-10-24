"""Мок-модель: детерминированные ответы по схеме. Нужна, чтобы весь поток работал без сети и бюджета.

Читает тот же <context>{json}</context>, что получает настоящая модель. Качество — заглушечное:
задача мока — проверять контракты и интеграцию, а не смысл.
"""

from __future__ import annotations

import json
import re

from pydantic import BaseModel


def _context(messages: list[dict]) -> dict:
    for m in reversed(messages):
        found = re.search(r"<context>\s*(.*?)\s*</context>", m.get("content", ""), flags=re.S)
        if found:
            return json.loads(found.group(1))
    return {}


def respond(schema: type[BaseModel], messages: list[dict]) -> dict:
    ctx = _context(messages)
    handler = _HANDLERS.get(schema.__name__)
    if handler is None:
        raise NotImplementedError(
            f"мок не умеет схему {schema.__name__} — добавьте обработчик в app/llm/mock.py"
        )
    return handler(ctx)


def _tag_news(ctx: dict) -> dict:
    title, body = ctx.get("title", "").lower(), ctx.get("text", "").lower()
    text = title + " " + body
    hits = []
    for f in ctx.get("factors", []):
        # ключевое слово должно начинать слово: иначе «порт» находится внутри «экспорт»
        in_title = sum(1 for kw in f.get("keywords", []) if re.search(r"\b" + re.escape(kw), title))
        in_body = sum(1 for kw in f.get("keywords", []) if re.search(r"\b" + re.escape(kw), body))
        if in_title or in_body:
            strength = 3 if in_title else 2 if in_body > 1 else 1
            hits.append((strength, in_title * 2 + in_body, f["id"]))
    hits.sort(reverse=True)
    up = any(w in text for w in ("вырос", "повыс", "рост", "превысил", "подорож", "максимум", "ужесточ"))
    down = any(w in text for w in ("снизил", "сниж", "замедл", "упал"))
    direction = "up" if up and not down else "down" if down and not up else "unclear"
    first = re.split(r"(?<=[.!?])\s+", ctx.get("text", ""))[0]
    return {
        "event_type": "macro" if hits and hits[0][2] in ("key_rate", "inflation") else "sector",
        "factors": [{"factor": fid, "direction": direction, "strength": st} for st, _, fid in hits[:4]],
        "sectors": sorted(
            {
                sec
                for f in ctx.get("factors", [])
                for st, _, fid in hits[:4]
                if fid == f["id"] and st == 3
                for sec in f.get("sectors", [])
            }
        ),
        "regions": [r for r in ctx.get("known_regions", []) if r.split()[0].lower()[:5] in text],
        "countries": [c for c in ("Китай", "Турция", "Казахстан") if c.lower()[:4] in text],
        "facts": [{"text": first, "quote": first}] if first else [],
    }


def _plan(ctx: dict) -> dict:
    factors = ctx.get("news_factors", [])
    steps = [
        {
            "tool": "search_bank",
            "args": {"query": ctx.get("title", ""), "factors": factors},
            "why": "позиция банка",
        },
        {"tool": "profile_facts", "args": {"factors": factors}, "why": "почему это важно компании"},
        {"tool": "bank_products", "args": {"factors": factors}, "why": "что можно сделать"},
    ]
    if ctx.get("has_counterparties"):
        steps.append({"tool": "counterparty_exposure", "args": {}, "why": "влияние через контрагентов"})
    else:
        steps.append({"tool": "related_news", "args": {"factors": factors, "days": 30}, "why": "контекст"})
    return {"steps": steps}


def _draft(ctx: dict) -> dict:
    ev = ctx.get("evidence", [])
    by = {t: [e for e in ev if e["type"] == t] for t in ("news", "bank", "profile", "product")}
    news = by["news"][:1]
    out: dict = {
        "what_happened": [],
        "why_it_matters": [],
        "risks": [],
        "opportunities": [],
        "actions": [],
        "bank_view": [],
    }
    if news:
        out["what_happened"].append(
            {
                "text": news[0]["quote"] or news[0]["title"],
                "kind": "fact",
                "source_ids": [news[0]["source_id"]],
            }
        )
    for p in by["profile"][:2]:
        out["why_it_matters"].append(
            {
                "text": f"Для вашей компании это важно: {p['quote']}.",
                "kind": "ai",
                "source_ids": [p["source_id"]] + [n["source_id"] for n in news],
            }
        )
    if not out["why_it_matters"] and news:
        out["why_it_matters"].append(
            {
                "text": "Прямой связи с профилем не найдено, новость общего фона.",
                "kind": "ai",
                "source_ids": [news[0]["source_id"]],
            }
        )
    direction = ctx.get("direction", "unclear")
    if news and by["profile"]:
        claim = {
            "text": "Возможен рост затрат или давление на маржу — оцените чувствительность бюджета."
            if direction == "up"
            else "Возможно изменение условий — следите за развитием событий.",
            "kind": "ai",
            "source_ids": [news[0]["source_id"], by["profile"][0]["source_id"]],
        }
        out["risks"].append(claim)
    for pr in by["product"][:2]:
        out["actions"].append(
            {"text": f"Обсудить с менеджером: {pr['title']}.", "kind": "ai", "source_ids": [pr["source_id"]]}
        )
    if not out["actions"] and news:
        out["actions"].append(
            {
                "text": "Действий не требуется, достаточно наблюдать.",
                "kind": "ai",
                "source_ids": [news[0]["source_id"]],
            }
        )
    for b in by["bank"][:2]:
        out["bank_view"].append({"text": b["quote"][:300], "kind": "bank", "source_ids": [b["source_id"]]})
    return out


def _judge(ctx: dict) -> dict:
    return {
        "verdicts": [
            {"claim_ref": c["ref"], "verdict": "supported", "reason": "mock"} for c in ctx.get("claims", [])
        ]
    }


def _chat(ctx: dict) -> dict:
    card = ctx.get("card", {})
    src = [s["source_id"] for s in card.get("sources", [])[:1]]
    return {
        "answer": f"[mock] По карточке «{card.get('title', '')}»: вопрос «{ctx.get('question', '')}» "
        "требует live-модели. Ниже — ключевой факт из карточки.",
        "claims": [
            {"text": c["text"], "kind": c["kind"], "source_ids": c["source_ids"]}
            for c in card.get("what_happened", [])[:1]
        ]
        if src
        else [],
    }


_HANDLERS = {
    "NewsTagsLLM": _tag_news,
    "Plan": _plan,
    "CardDraft": _draft,
    "JudgeResult": _judge,
    "ChatAnswer": _chat,
}
