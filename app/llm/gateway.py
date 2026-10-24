"""LLM-шлюз — ЕДИНСТВЕННАЯ точка вызова моделей.

Что делает (идея Task.output_pydantic + guardrail + max_retry_limit из CrewAI):
  1. добавляет к промпту JSON-схему ответа;
  2. кэширует ответ по hash(model, messages, schema, temperature);
  3. проверяет дневной бюджет и квоту владельца ДО вызова;
  4. парсит JSON (с ремонтом), валидирует pydantic + доп. валидаторы;
  5. при ошибке возвращает модели текст ошибки и повторяет (max_retries);
  6. пишет каждый вызов в трассу (модель, токены, рубли, кэш).

TODO C: проверить в день 1 — API организаторов OpenAI-совместимый (/chat/completions)? response_format?
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Callable, Sequence
from datetime import date
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app import store
from app.config import settings
from app.llm import mock, trace

T = TypeVar("T", bound=BaseModel)
Validator = Callable[[BaseModel], list[str]]


class BudgetExceeded(RuntimeError):
    pass


class LLMFailed(RuntimeError):
    pass


def _schema_instruction(schema: type[BaseModel]) -> str:
    js = json.dumps(schema.model_json_schema(), ensure_ascii=False)
    return "Ответь ОДНИМ JSON-объектом без пояснений и без markdown, строго по JSON Schema:\n" + js


def _cache_key(model: str, messages: list[dict], schema: type[BaseModel], temperature: float) -> str:
    raw = json.dumps([model, messages, schema.__name__, temperature], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def extract_json(text: str) -> dict:
    """Ремонт типовых поломок: ```json-обёртка, текст до/после, <think>-блоки."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])


def spent_today(owner: str | None = None) -> float:
    q = "SELECT COALESCE(SUM(cost_rub), 0) FROM budget WHERE day = ?"
    params: tuple = (date.today().isoformat(),)
    if owner:
        q += " AND owner = ?"
        params += (owner,)
    return float(store.raw(q, params)[0][0])


def _check_budget() -> None:
    s = settings()
    if spent_today() >= s.daily_budget_rub:
        raise BudgetExceeded(f"дневной бюджет {s.daily_budget_rub} ₽ исчерпан")
    quota = s.budget_quotas.get(s.llm_owner)
    if quota is not None and spent_today(s.llm_owner) >= quota:
        raise BudgetExceeded(f"квота {s.llm_owner} = {quota} ₽ исчерпана")


def _cost(alias: str, tin: int, tout: int) -> float:
    p = settings().prices.get(alias)
    return 0.0 if not p else (tin * p[0] + tout * p[1]) / 1000


def _call_live(alias: str, messages: list[dict], temperature: float) -> tuple[str, int, int]:
    s = settings()
    if not s.llm_base_url:
        raise LLMFailed("LLM_MODE=live, но LLM_BASE_URL не задан")
    body: dict = {"model": s.models[alias], "messages": messages, "temperature": temperature}
    if s.llm_json_mode:
        body["response_format"] = {"type": "json_object"}
    r = httpx.post(
        s.llm_base_url.rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {s.llm_api_key}"},
        json=body,
        timeout=s.llm_timeout_s,
    )
    r.raise_for_status()
    data = r.json()
    usage = data.get("usage") or {}
    return (
        data["choices"][0]["message"]["content"] or "",
        int(usage.get("prompt_tokens", 0)),
        int(usage.get("completion_tokens", 0)),
    )


def call_structured(
    alias: str,
    messages: list[dict],
    schema: type[T],
    *,
    validators: Sequence[Validator] = (),
    max_retries: int = 2,
    temperature: float = 0.0,
    step: str = "llm",
) -> T:
    s = settings()
    if alias not in s.models:
        raise ValueError(f"неизвестная модель '{alias}', есть: {list(s.models)}")
    msgs = [{"role": "system", "content": _schema_instruction(schema)}, *messages]
    last_error = ""
    for attempt in range(max_retries + 1):
        key = _cache_key(s.models[alias] + "|" + s.llm_mode, msgs, schema, temperature)
        hit = store.raw("SELECT response FROM llm_cache WHERE key = ?", (key,))
        t0 = time.monotonic()
        tin = tout = 0
        if hit:
            content, cached = hit[0][0], True
        else:
            cached = False
            if s.llm_mode == "live":
                _check_budget()
                content, tin, tout = _call_live(alias, msgs, temperature)
            else:
                content = json.dumps(mock.respond(schema, msgs), ensure_ascii=False)
        cost = _cost(alias, tin, tout)
        try:
            obj = schema.model_validate(extract_json(content))
            issues = [i for v in validators for i in v(obj)]
        except (json.JSONDecodeError, ValidationError) as e:
            obj, issues = None, [f"невалидный ответ: {str(e)[:500]}"]
        ok = not issues
        if not cached and ok:
            with store.conn() as c:
                c.execute("INSERT OR REPLACE INTO llm_cache(key, response) VALUES (?, ?)", (key, content))
        if not cached and (tin or tout or cost):
            with store.conn() as c:
                c.execute(
                    "INSERT INTO budget VALUES (?, ?, ?, ?, ?, ?)",
                    (date.today().isoformat(), s.llm_owner, alias, cost, tin, tout),
                )
        trace.emit(
            step,
            model=alias,
            tokens_in=tin,
            tokens_out=tout,
            cost_rub=cost,
            cached=cached,
            ok=ok,
            detail={
                "attempt": attempt,
                "schema": schema.__name__,
                "issues": issues[:5],
                "ms": int((time.monotonic() - t0) * 1000),
            },
        )
        if ok:
            return obj  # type: ignore[return-value]
        last_error = "; ".join(issues)
        msgs = [
            *msgs,
            {"role": "assistant", "content": content[:4000]},
            {
                "role": "user",
                "content": f"Ответ не прошёл проверку: {last_error}. Исправь и верни JSON заново.",
            },
        ]
    raise LLMFailed(f"{schema.__name__}: не удалось за {max_retries + 1} попыток: {last_error}")


def context_block(data: dict) -> str:
    """Контекст для модели в машиночитаемом виде. Мок-режим читает его же."""
    return "<context>\n" + json.dumps(data, ensure_ascii=False, default=str) + "\n</context>"
