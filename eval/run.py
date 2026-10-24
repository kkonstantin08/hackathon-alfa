"""Оценка качества: python -m eval.run [--k 5] [--cards]

Метрики:
  ranking: precision@k и recall@k по размеченным парам (company, news, relevant)
  cards (--cards): доля карточек, прошедших самопроверку, среднее число попыток и выкинутых утверждений

gold.jsonl размечает команда (A + C) в день 3 на новостях, которых не было в разработке.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from app.agent.flow import build_card
from app.ranking.feed import feed


def main(argv: list[str] | None = None) -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", type=Path, default=Path(__file__).parent / "gold.jsonl")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--cards", action="store_true")
    a = ap.parse_args(argv)
    gold = [json.loads(x) for x in a.gold.read_text(encoding="utf-8").splitlines() if x.strip()]

    by_company = defaultdict(list)
    for g in gold:
        by_company[g["company_id"]].append(g)
    p_at_k, r_at_k, misses = [], [], []
    for cid, items in by_company.items():
        top = [r.news_id for r in feed(cid, a.k)]
        rel = {g["news_id"] for g in items if g["relevant"]}
        irr = {g["news_id"] for g in items if not g["relevant"]}
        judged = [n for n in top if n in rel | irr]
        if judged:
            p_at_k.append(sum(n in rel for n in judged) / len(judged))
        if rel:
            r_at_k.append(len(rel & set(top)) / len(rel))
        misses += [
            f"{cid}: нет в топ-{a.k} {g['news_id']} ({g['note']})"
            for g in items
            if g["relevant"] and g["news_id"] not in top
        ]
        misses += [
            f"{cid}: лишняя в топ-{a.k} {g['news_id']} ({g['note']})"
            for g in items
            if not g["relevant"] and g["news_id"] in top
        ]
    report: dict = {
        "ranking": {
            f"precision@{a.k}": round(sum(p_at_k) / max(len(p_at_k), 1), 3),
            f"recall@{a.k}": round(sum(r_at_k) / max(len(r_at_k), 1), 3),
            "errors": misses,
        },
    }
    if a.cards:
        cards = [build_card(g["company_id"], g["news_id"]) for g in gold if g["relevant"]]
        report["cards"] = {
            "n": len(cards),
            "self_check_passed": round(sum(c.self_check.passed for c in cards) / max(len(cards), 1), 3),
            "avg_attempts": round(sum(c.self_check.attempts for c in cards) / max(len(cards), 1), 2),
            "dropped_claims": sum(len(c.self_check.dropped_claims) for c in cards),
        }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    main()
