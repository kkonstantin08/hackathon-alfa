"""Самопроверка карточки: слой 1 — код, слой 2 — Gemma-судья. Неподтверждённое выкидываем."""

from __future__ import annotations

import re

from app.agent import prompts
from app.llm.gateway import call_structured
from contracts.models import CardDraft, Claim, JudgeResult, Source

BLOCKS = ("what_happened", "why_it_matters", "risks", "opportunities", "actions", "bank_view")
REQUIRED = ("what_happened", "why_it_matters", "actions")
_NUM = re.compile(r"\d+(?:[.,]\d+)?")


def iter_claims(d: CardDraft):
    for b in BLOCKS:
        for i, c in enumerate(getattr(d, b)):
            yield f"{b}:{i}", b, c


def _norm_num(s: str) -> str:
    return s.replace(",", ".")


def claim_issues(ref: str, c: Claim, pool: dict[str, Source], full: dict[str, str]) -> list[str]:
    issues = []
    unknown = [s for s in c.source_ids if s not in pool]
    if unknown:
        issues.append(f"{ref}: несуществующие source_ids {unknown}")
    types = {pool[s].type for s in c.source_ids if s in pool}
    if c.kind == "fact" and "news" not in types:
        issues.append(f"{ref}: kind=fact должен ссылаться на news:*")
    if c.kind == "bank" and "bank" not in types:
        issues.append(f"{ref}: kind=bank должен ссылаться на bank:*")
    cited = " ".join(
        full.get(s, "") + " " + pool[s].quote + " " + pool[s].title for s in c.source_ids if s in pool
    )
    cited_nums = {_norm_num(n) for n in _NUM.findall(cited)}
    bad = [n for n in _NUM.findall(c.text) if _norm_num(n) not in cited_nums]
    if bad:
        issues.append(f"{ref}: числа {bad} не встречаются в цитируемых источниках")
    return issues


def static(d: CardDraft, pool: dict[str, Source], full: dict[str, str]) -> list[str]:
    issues = [i for ref, _, c in iter_claims(d) for i in claim_issues(ref, c, pool, full)]
    if any(s.type == "bank" for s in pool.values()) and not d.bank_view:
        issues.append("bank_view пуст, хотя в evidence есть материалы банка")
    return issues


def judge(d: CardDraft, pool: dict[str, Source], full: dict[str, str]) -> tuple[list[str], set[str]]:
    claims = [
        {
            "ref": ref,
            "text": c.text,
            "kind": c.kind,
            "quotes": [full.get(s) or pool[s].quote for s in c.source_ids if s in pool],
        }
        for ref, _, c in iter_claims(d)
    ]
    res = call_structured(
        "gemma", prompts.msgs(prompts.JUDGE, {"claims": claims}), JudgeResult, step="agent.judge"
    )
    bad = {v.claim_ref for v in res.verdicts if v.verdict == "unsupported"}
    return [
        f"{v.claim_ref}: судья — {v.verdict}: {v.reason}" for v in res.verdicts if v.verdict == "unsupported"
    ], bad


def drop_unsupported(
    d: CardDraft, pool: dict[str, Source], full: dict[str, str], judged_bad: set[str]
) -> tuple[CardDraft, list[str]]:
    dropped: list[str] = []
    data = {}
    for b in BLOCKS:
        keep = []
        for i, c in enumerate(getattr(d, b)):
            ref = f"{b}:{i}"
            if claim_issues(ref, c, pool, full) or ref in judged_bad:
                dropped.append(f"{ref}: {c.text[:80]}")
            else:
                keep.append(c)
        data[b] = keep
    # обязательные блоки не должны опустеть: подставляем безопасный факт из новости
    news_src = next((s for s in pool.values() if s.type == "news"), None)
    for b in REQUIRED:
        if not data[b] and news_src:
            text = {
                "what_happened": news_src.quote or news_src.title,
                "why_it_matters": "Связь с профилем компании не подтверждена — новость фоновая.",
                "actions": "Специальных действий не требуется, наблюдать за развитием.",
            }[b]
            data[b] = [
                Claim(
                    text=text, kind="fact" if b == "what_happened" else "ai", source_ids=[news_src.source_id]
                )
            ]
    return CardDraft.model_validate(data), dropped
