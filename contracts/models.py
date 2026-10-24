"""Контракты между модулями. Единственное место, где описаны данные, которые ходят между людьми.

Правило: поле можно ДОБАВИТЬ (с дефолтом) без согласования. Переименовать/удалить/сменить тип —
только через PR с одобрением владельца контрактов (роль C). Временные поля кладите в `extra`.
"""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator

CONTRACTS_DIR = Path(__file__).parent

Level = Literal["low", "medium", "high"]
Direction = Literal["up", "down", "neutral", "unclear"]
ClaimKind = Literal["fact", "bank", "ai"]
SourceType = Literal["news", "bank", "profile", "product"]


@lru_cache
def factor_ids() -> frozenset[str]:
    data = yaml.safe_load((CONTRACTS_DIR / "factors.yaml").read_text(encoding="utf-8"))
    return frozenset(f["id"] for f in data["factors"])


def _check_factor(v: str) -> str:
    if v not in factor_ids():
        raise ValueError(f"неизвестный фактор '{v}', допустимые: {sorted(factor_ids())}")
    return v


# ---------- Профиль компании (M1 profiles) ----------


class Evidence(BaseModel):
    field: str
    value: Any


class Exposure(BaseModel):
    factor: str
    level: Level
    why: str
    evidence: list[Evidence] = []

    @field_validator("factor")
    @classmethod
    def _known_factor(cls, v: str) -> str:
        return _check_factor(v)


class Counterparty(BaseModel):
    company_id: str
    okved_code: str | None = None
    share: float = Field(ge=0, le=1, description="доля в оборотах компании")
    role: Literal["supplier", "buyer"]


class CompanyProfile(BaseModel):
    company_id: str
    display_name: str
    okved_code: str
    okved_name: str
    region: str | None = None
    city: str | None = None
    revenue: float | None = None
    workers_gradation: str | None = None
    client_type: str | None = None
    products: dict[str, bool] = {}
    fts_flag: bool = False
    fts_country: str | None = None
    group_id: str | None = None
    group_member_ids: list[str] = []
    counterparties: list[Counterparty] = []
    exposures: list[Exposure] = []
    extra: dict[str, Any] = {}


# ---------- Новости (M2 news) ----------


class NewsItem(BaseModel):
    news_id: str
    url: str
    source: str
    published_at: datetime
    title: str
    text: str
    extra: dict[str, Any] = {}


class FactorTag(BaseModel):
    factor: str
    direction: Direction
    strength: int = Field(ge=1, le=3, description="1 — фон, 3 — прямое сильное влияние")

    @field_validator("factor")
    @classmethod
    def _known_factor(cls, v: str) -> str:
        return _check_factor(v)


class Fact(BaseModel):
    text: str
    quote: str = Field(description="дословная цитата из текста новости")


class NewsTagsLLM(BaseModel):
    """То, что возвращает модель при разметке (без служебных полей)."""

    event_type: str
    factors: list[FactorTag] = Field(max_length=5)
    sectors: list[str] = Field(default=[], description="коды ОКВЭД (2–4 знака) затронутых отраслей")
    regions: list[str] = []
    countries: list[str] = []
    facts: list[Fact] = Field(default=[], max_length=5)


class NewsTags(NewsTagsLLM):
    news_id: str
    cluster_id: str | None = None
    tagger: str = "unknown"


# ---------- Ранжирование (M4 ranking) ----------


class Reason(BaseModel):
    factor: str | None = None
    text: str
    contribution: float


class RankedNews(BaseModel):
    company_id: str
    news_id: str
    title: str
    source: str
    published_at: datetime
    score: float
    reasons: list[Reason]


# ---------- База знаний банка (M3 bank_kb) ----------


class BankSnippet(BaseModel):
    chunk_id: str = Field(description="doc_id#n")
    doc_id: str
    doc_title: str
    date: Date | None = None
    page: int | None = None
    text: str
    factors: list[str] = []
    score: float = 0.0


# ---------- Агент и карточка (M5 agent) ----------

ToolName = Literal["search_bank", "related_news", "profile_facts", "counterparty_exposure", "bank_products"]


class PlanStep(BaseModel):
    tool: ToolName
    args: dict[str, Any] = {}
    why: str = ""


class Plan(BaseModel):
    steps: list[PlanStep] = Field(min_length=1, max_length=4)


class Source(BaseModel):
    source_id: str
    type: SourceType
    ref: str = Field(description="url новости, chunk_id банка, поле профиля, id продукта")
    title: str = ""
    quote: str = ""


class Claim(BaseModel):
    text: str
    kind: ClaimKind
    source_ids: list[str] = Field(min_length=1)


class CardDraft(BaseModel):
    """То, что пишет модель. Источники и проверку добавляет код."""

    what_happened: list[Claim] = Field(min_length=1)
    why_it_matters: list[Claim] = Field(min_length=1)
    risks: list[Claim] = []
    opportunities: list[Claim] = []
    actions: list[Claim] = Field(min_length=1)
    bank_view: list[Claim] = []


class SelfCheck(BaseModel):
    passed: bool
    attempts: int
    issues: list[str] = []
    dropped_claims: list[str] = []


class AnalysisCard(CardDraft):
    card_id: str
    company_id: str
    news_id: str
    title: str
    sources: list[Source]
    self_check: SelfCheck
    trace_id: str
    created_at: datetime


class ClaimVerdict(BaseModel):
    claim_ref: str = Field(description="block:index, например why_it_matters:0")
    verdict: Literal["supported", "partial", "unsupported"]
    reason: str = ""


class JudgeResult(BaseModel):
    verdicts: list[ClaimVerdict]


class ChatAnswer(BaseModel):
    answer: str
    claims: list[Claim] = []


# ---------- Трасса ----------


class TraceEvent(BaseModel):
    trace_id: str
    step: str
    ts: datetime
    model: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_rub: float = 0.0
    cached: bool = False
    ok: bool = True
    detail: dict[str, Any] = {}
