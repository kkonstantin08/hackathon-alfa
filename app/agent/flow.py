"""M5 agent: карточка новости для компании. Свой цикл: план → инструменты → черновик → проверка → ретрай.

Идея Flow из CrewAI в минимальном виде: явное состояние (CardState) + список шагов + раннер,
который пишет каждый шаг в трассу. Декораторы @start/@listen не нужны: поток линейный с одним циклом.

Публичное API:
    build_card(company_id, news_id, refresh=False) -> AnalysisCard
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app import store
from app.agent import checks, prompts, tools
from app.llm import trace
from app.llm.gateway import LLMFailed, call_structured
from app.news import pipeline as news
from app.profiles import build as profiles
from contracts.models import AnalysisCard, CardDraft, Plan, PlanStep, SelfCheck, Source

PLAN_MODEL = os.environ.get("PLAN_MODEL", "qwen")
DRAFT_MODEL = os.environ.get("DRAFT_MODEL", "glm")
MAX_DRAFT_ATTEMPTS = 3

# Запасной план, если планировщик сломался: фиксированная цепочка (см. «Когда упрощать»).
FALLBACK_PLAN = Plan(
    steps=[
        PlanStep(tool="search_bank", why="fallback"),
        PlanStep(tool="profile_facts", why="fallback"),
        PlanStep(tool="bank_products", why="fallback"),
        PlanStep(tool="related_news", why="fallback"),
    ]
)


@dataclass
class CardState:
    ctx: tools.ToolContext
    trace_id: str
    plan: Plan | None = None
    pool: dict[str, Source] = field(default_factory=dict)
    draft: CardDraft | None = None
    feedback: list[str] = field(default_factory=list)
    attempts: int = 0
    passed: bool = False
    dropped: list[str] = field(default_factory=list)

    def add(self, sources: list[Source]) -> None:
        for s in sources:
            self.pool.setdefault(s.source_id, s)


def _base_ctx(st: CardState) -> dict:
    p, n, t = st.ctx.profile, st.ctx.item, st.ctx.tags
    return {
        "company": {
            "okved": f"{p.okved_code} {p.okved_name}",
            "region": p.region,
            "products": p.products,
            "fts_country": p.fts_country,
            "exposures": [{"factor": e.factor, "level": e.level, "why": e.why} for e in p.exposures],
        },
        "news": {"title": n.title, "published_at": n.published_at, "text": n.text[:4000]},
        "news_factors": [f.model_dump() for f in t.factors],
    }


def step_plan(st: CardState) -> None:
    ctx = {
        **_base_ctx(st),
        "tools": tools.describe(),
        "title": st.ctx.item.title,
        "news_factors": st.ctx.news_factors,
        "has_counterparties": bool(st.ctx.profile.counterparties),
    }
    try:
        st.plan = call_structured(PLAN_MODEL, prompts.msgs(prompts.PLAN, ctx), Plan, step="agent.plan")
    except LLMFailed as e:
        trace.emit("agent.plan.fallback", ok=False, detail={"error": str(e)[:300]})
        st.plan = FALLBACK_PLAN


def step_tools(st: CardState) -> None:
    st.add([tools.news_source(st.ctx.item, st.ctx.tags)])
    st.ctx.full_text[f"news:{st.ctx.item.news_id}"] = st.ctx.item.title + " " + st.ctx.item.text
    assert st.plan
    for s in st.plan.steps[:4]:
        st.add(tools.run_tool(st.ctx, s.tool, s.args))
    if not any(s.type == "profile" for s in st.pool.values()):  # почему-важно без профиля не написать
        st.add(tools.run_tool(st.ctx, "profile_facts", {}))


def step_draft_and_check(st: CardState) -> None:
    judged_bad: set[str] = set()
    for attempt in range(1, MAX_DRAFT_ATTEMPTS + 1):
        st.attempts = attempt
        dir_ = st.ctx.tags.factors[0].direction if st.ctx.tags.factors else "unclear"
        ctx = {
            **_base_ctx(st),
            "evidence": [s.model_dump() for s in st.pool.values()],
            "direction": dir_,
            "feedback": st.feedback,
        }
        st.draft = call_structured(
            DRAFT_MODEL,
            prompts.msgs(prompts.DRAFT, ctx),
            CardDraft,
            step="agent.draft",
            temperature=0.2 if attempt == 1 else 0.0,
        )
        issues = checks.static(st.draft, st.pool, st.ctx.full_text)
        j_issues, judged_bad = checks.judge(st.draft, st.pool, st.ctx.full_text)
        issues += j_issues
        trace.emit("agent.check", ok=not issues, detail={"attempt": attempt, "issues": issues[:10]})
        if not issues:
            st.passed = True
            break
        st.feedback = issues
    assert st.draft
    st.draft, st.dropped = checks.drop_unsupported(st.draft, st.pool, st.ctx.full_text, judged_bad)


STEPS: list[tuple[str, Callable[[CardState], None]]] = [
    ("plan", step_plan),
    ("tools", step_tools),
    ("draft_check", step_draft_and_check),
]


def _cache_key(company_id: str, news_id: str) -> str:
    return f"{company_id}:{news_id}"


def build_card(company_id: str, news_id: str, refresh: bool = False) -> AnalysisCard:
    key = _cache_key(company_id, news_id)
    if not refresh and (cached := store.get("cards", key, AnalysisCard)):
        return cached
    profile, item, tg = profiles.get(company_id), news.get(news_id), news.tags(news_id)
    if not (profile and item and tg):
        raise KeyError(f"нет данных: company={bool(profile)} news={bool(item)} tags={bool(tg)}")
    tid = trace.new_trace("card")
    st = CardState(ctx=tools.ToolContext(profile, item, tg), trace_id=tid)
    for name, fn in STEPS:
        trace.emit(f"step.{name}.start")
        fn(st)
        trace.emit(f"step.{name}.end")
    assert st.draft
    used = {s for _, _, c in checks.iter_claims(st.draft) for s in c.source_ids}
    card = AnalysisCard(
        **st.draft.model_dump(),
        card_id=key,
        company_id=company_id,
        news_id=news_id,
        title=item.title,
        sources=[s for sid, s in st.pool.items() if sid in used],
        self_check=SelfCheck(
            passed=st.passed and not st.dropped,
            attempts=st.attempts,
            issues=st.feedback if not st.passed else [],
            dropped_claims=st.dropped,
        ),
        trace_id=tid,
        created_at=datetime.now(UTC),
    )
    store.put("cards", key, card)
    return card
