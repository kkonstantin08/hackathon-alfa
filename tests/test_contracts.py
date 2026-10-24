"""Контракты и fixtures согласованы: сломать их незаметно нельзя."""

import json

import yaml

from app.config import settings
from contracts.models import BankSnippet, NewsItem, factor_ids


def test_rules_reference_known_factors():
    rules = yaml.safe_load((settings().contracts_dir / "exposure_rules.yaml").read_text(encoding="utf-8"))
    used = {r["factor"] for block in ("products", "foreign_trade", "okved") for r in rules[block]}
    used.add(rules["regional"]["factor"])
    assert used <= factor_ids(), used - factor_ids()


def test_products_reference_known_factors():
    prods = yaml.safe_load((settings().fixtures_dir / "bank_products.yaml").read_text(encoding="utf-8"))
    used = {f for p in prods["products"] for f in p["factors"]}
    assert used <= factor_ids(), used - factor_ids()


def test_fixtures_validate():
    fx = settings().fixtures_dir
    for line in (fx / "news.jsonl").read_text(encoding="utf-8").splitlines():
        NewsItem.model_validate(json.loads(line))
    for line in (fx / "bank_chunks.jsonl").read_text(encoding="utf-8").splitlines():
        c = BankSnippet.model_validate(json.loads(line))
        assert set(c.factors) <= factor_ids()


def test_factor_count_reasonable():
    assert 15 <= len(factor_ids()) <= 25
