"""M7 api: тонкая HTTP-обёртка над публичными функциями модулей. Бизнес-логики здесь нет."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.agent import chat as chat_mod
from app.agent import flow
from app.config import ROOT, settings
from app.llm import gateway, trace
from app.llm.gateway import BudgetExceeded, LLMFailed
from app.profiles import build as profiles
from app.ranking import feed as ranking
from contracts.models import AnalysisCard, ChatAnswer, CompanyProfile, RankedNews, TraceEvent

app = FastAPI(
    title="Alfa News Analytics",
    version="0.1.0",
    description="Персональная новостная аналитика для руководителей бизнеса",
)


class CompanyBrief(BaseModel):
    company_id: str
    display_name: str
    okved_name: str
    region: str | None
    top_factors: list[str]


class ChatRequest(BaseModel):
    card_id: str
    message: str
    history: list[dict] = []


class ChatResponse(BaseModel):
    answer: ChatAnswer
    trace_id: str


@app.get("/api/health")
def health() -> dict:
    s = settings()
    return {
        "ok": True,
        "llm_mode": s.llm_mode,
        "spent_today_rub": round(gateway.spent_today(), 2),
        "daily_budget_rub": s.daily_budget_rub,
    }


@app.get("/api/companies", response_model=list[CompanyBrief])
def companies() -> list[CompanyBrief]:
    return [
        CompanyBrief(
            company_id=p.company_id,
            display_name=p.display_name,
            okved_name=p.okved_name,
            region=p.region,
            top_factors=[e.factor for e in p.exposures[:4]],
        )
        for p in profiles.all_profiles()
    ]


@app.get("/api/companies/{company_id}", response_model=CompanyProfile)
def company(company_id: str) -> CompanyProfile:
    p = profiles.get(company_id)
    if not p:
        raise HTTPException(404, "компания не найдена")
    return p


@app.get("/api/feed", response_model=list[RankedNews])
def feed(company_id: str, k: int = 20) -> list[RankedNews]:
    try:
        return ranking.feed(company_id, k)
    except KeyError as e:
        raise HTTPException(404, "компания не найдена") from e


@app.get("/api/cards/{company_id}/{news_id}", response_model=AnalysisCard)
def card(company_id: str, news_id: str, refresh: bool = False) -> AnalysisCard:
    try:
        return flow.build_card(company_id, news_id, refresh=refresh)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    except BudgetExceeded as e:
        raise HTTPException(429, str(e)) from e
    except LLMFailed as e:
        raise HTTPException(502, str(e)) from e


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    try:
        ans, tid = chat_mod.chat(req.card_id, req.message, req.history)
        return ChatResponse(answer=ans, trace_id=tid)
    except KeyError as e:
        raise HTTPException(404, "сначала откройте карточку") from e
    except BudgetExceeded as e:
        raise HTTPException(429, str(e)) from e
    except LLMFailed as e:
        raise HTTPException(502, str(e)) from e


@app.get("/api/trace/{trace_id}", response_model=list[TraceEvent])
def get_trace(trace_id: str) -> list[TraceEvent]:
    return trace.get(trace_id)


WEB = Path(ROOT / "web")
app.mount("/static", StaticFiles(directory=WEB), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")
