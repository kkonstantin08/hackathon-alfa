"""Офлайн-конвейер: python -m app.ingest [--companies ...] [--payments ...] [--news ...] [--bank ...]

По умолчанию берёт fixtures/. Повторный запуск дешёвый: разметка новостей кэшируется в llm-шлюзе.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.bank_kb import kb
from app.config import settings
from app.news import pipeline as news
from app.profiles import build as profiles


def main(argv: list[str] | None = None) -> dict:
    fx = settings().fixtures_dir
    ap = argparse.ArgumentParser()
    ap.add_argument("--companies", type=Path, default=fx / "companies.csv")
    ap.add_argument("--payments", type=Path, default=fx / "payments.csv")
    ap.add_argument("--news", type=Path, default=fx / "news.jsonl")
    ap.add_argument(
        "--bank",
        type=Path,
        default=fx / "bank_chunks.jsonl",
        help="jsonl с готовыми чанками (папку с PDF подключит B)",
    )
    a = ap.parse_args(argv)

    ps = profiles.build(a.companies, a.payments)
    profiles.save(ps)
    regions = sorted({p.region for p in ps if p.region})

    items = news.load(a.news)
    tags = [news.tag(i, known_regions=regions) for i in items]
    clusters = news.dedup(items, {t.news_id: t for t in tags})
    for t in tags:
        t.cluster_id = clusters.get(t.news_id)
    news.save(items, tags)

    kb.save(kb.load_chunks(a.bank))

    report = {
        "profiles": profiles.diversity_report(ps),
        "news": len(items),
        "news_untagged": sum(1 for t in tags if not t.factors),
        "clusters": len(set(clusters.values())),
        "bank_chunks": len(kb.load_chunks(a.bank)),
        "llm_mode": settings().llm_mode,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    main()
