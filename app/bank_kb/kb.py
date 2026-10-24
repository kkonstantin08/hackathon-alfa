"""M3 bank_kb: материалы банка → чанки с факторами → поиск (фильтр по факторам + BM25).

Публичное API:
    load_chunks(jsonl) -> list[BankSnippet]           # готовые чанки (fixtures)
    chunk_pdf(path, doc_id, title, date) -> list[BankSnippet]   # нарезка PDF (pip install .[pdf])
    tag_chunks(chunks) -> list[BankSnippet]           # TODO B: факторы чанкам через Gemma
    save(chunks), search(query, factors, k=5) -> list[BankSnippet]

Почему так: 9 документов ≈ 150–300 чанков. После фильтра по фактору остаётся 5–15,
поэтому разметка факторами важнее модели поиска. Эмбеддинги — второй слой (EMBEDDINGS=on, TODO B).
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from datetime import date
from pathlib import Path

import snowballstemmer

from app import store
from contracts.models import BankSnippet


def load_chunks(path: Path) -> list[BankSnippet]:
    with open(path, encoding="utf-8") as f:
        return [BankSnippet.model_validate(json.loads(line)) for line in f if line.strip()]


def chunk_pdf(
    path: Path, doc_id: str, title: str, doc_date: date | None = None, max_chars: int = 2500
) -> list[BankSnippet]:
    """Нарезка по страницам/абзацам до ~max_chars. Нарезку по заголовкам доработать на реальных PDF."""
    from pypdf import PdfReader  # BSD-3; PyMuPDF не используем из-за AGPL

    chunks: list[BankSnippet] = []
    for page_no, page in enumerate(PdfReader(str(path)).pages, 1):
        buf = ""
        for para in re.split(r"\n\s*\n", page.extract_text() or ""):
            if len(buf) + len(para) > max_chars and buf:
                chunks.append(_mk(doc_id, title, doc_date, page_no, buf, len(chunks) + 1))
                buf = ""
            buf += para.strip() + "\n"
        if buf.strip():
            chunks.append(_mk(doc_id, title, doc_date, page_no, buf, len(chunks) + 1))
    return chunks


def _mk(doc_id, title, d, page, text, n) -> BankSnippet:
    return BankSnippet(
        chunk_id=f"{doc_id}#{n}", doc_id=doc_id, doc_title=title, date=d, page=page, text=text.strip()
    )


def save(chunks: list[BankSnippet]) -> None:
    store.clear("bank_chunks")
    store.put_many("bank_chunks", [(c.chunk_id, c) for c in chunks])
    _Index.reset()


_stem = snowballstemmer.stemmer("russian").stemWord


def _tok(s: str) -> list[str]:
    # стемминг Snowball (BSD-3). Если не хватит — pymorphy3-лемматизация (TODO B)
    return [_stem(w) for w in re.findall(r"\w+", s.lower()) if len(w) > 2]


class _Index:
    _inst: _Index | None = None

    def __init__(self) -> None:
        self.chunks = store.all_("bank_chunks", BankSnippet)
        self.docs = [_tok(c.doc_title + " " + c.text) for c in self.chunks]
        self.avgdl = sum(map(len, self.docs)) / max(len(self.docs), 1)
        df = Counter(t for d in self.docs for t in set(d))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - v + 0.5) / (v + 0.5)) for t, v in df.items()}
        self.tf = [Counter(d) for d in self.docs]

    @classmethod
    def get(cls) -> _Index:
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst

    @classmethod
    def reset(cls) -> None:
        cls._inst = None

    def bm25(self, q: list[str], i: int, k1: float = 1.5, b: float = 0.75) -> float:
        tf, dl = self.tf[i], len(self.docs[i])
        return sum(
            self.idf.get(t, 0) * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * dl / self.avgdl))
            for t in q
            if t in tf
        )


def search(query: str, factors: list[str] | None = None, k: int = 5) -> list[BankSnippet]:
    """factors — по убыванию важности: первый фактор весит больше остальных."""
    idx = _Index.get()
    weight = {f: (3.0 if i == 0 else 1.0) for i, f in enumerate(factors or [])}
    q = _tok(query)
    scored = []
    for i, c in enumerate(idx.chunks):
        overlap = sum(weight.get(f, 0.0) for f in c.factors)
        if factors and not overlap:
            continue
        s = idx.bm25(q, i) + overlap
        scored.append((s, c))
    scored.sort(key=lambda x: -x[0])
    return [c.model_copy(update={"score": round(s, 3)}) for s, c in scored[:k]]
