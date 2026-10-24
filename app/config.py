"""Все настройки из окружения. Список переменных — в .env.example."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    # mock — без сети, детерминированные ответы; live — реальные модели организаторов
    llm_mode: str = field(default_factory=lambda: _env("LLM_MODE", "mock"))
    llm_base_url: str = field(default_factory=lambda: _env("LLM_BASE_URL", ""))
    llm_api_key: str = field(default_factory=lambda: _env("LLM_API_KEY", ""))
    llm_timeout_s: float = field(default_factory=lambda: float(_env("LLM_TIMEOUT_S", "60")))
    llm_json_mode: bool = field(default_factory=lambda: _env("LLM_JSON_MODE", "1") == "1")
    # алиас → реальное имя модели у провайдера
    models: dict[str, str] = field(
        default_factory=lambda: {
            "gemma": _env("MODEL_GEMMA", "gemma-4-26b-a4b"),
            "qwen": _env("MODEL_QWEN", "qwen3.6-35b-a3b"),
            "glm": _env("MODEL_GLM", "glm-5.3-flash"),
            "kimi": _env("MODEL_KIMI", "kimi-k2.6"),
            "deepseek": _env("MODEL_DEEPSEEK", "deepseek-v4.1-flash"),
            "qwen_vl": _env("MODEL_QWEN_VL", "qwen3-vl-30b-a3b-instruct"),
        }
    )
    # руб. за 1000 токенов {"gemma": [in, out], ...}; цены уточнить у организаторов
    prices: dict[str, list[float]] = field(
        default_factory=lambda: json.loads(_env("LLM_PRICES_RUB_PER_1K", "{}"))
    )
    daily_budget_rub: float = field(default_factory=lambda: float(_env("DAILY_BUDGET_RUB", "450")))
    budget_quotas: dict[str, float] = field(default_factory=lambda: json.loads(_env("BUDGET_QUOTAS", "{}")))
    llm_owner: str = field(default_factory=lambda: _env("LLM_OWNER", "shared"))
    db_path: Path = field(default_factory=lambda: Path(_env("DB_PATH", str(ROOT / "data" / "app.db"))))
    fixtures_dir: Path = ROOT / "fixtures"
    contracts_dir: Path = ROOT / "contracts"
    # «сейчас» для свежести новостей; пусто = последняя дата в корпусе
    now: str = field(default_factory=lambda: _env("NOW", ""))
    embeddings: str = field(default_factory=lambda: _env("EMBEDDINGS", "off"))


def settings() -> Settings:
    return Settings()
