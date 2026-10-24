"""SQLite-хранилище. Каждая таблица — id + JSON pydantic-модели. Модули пишут только в свои таблицы."""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from app.config import settings

T = TypeVar("T", bound=BaseModel)

DOC_TABLES = ("companies", "news", "news_tags", "bank_chunks", "cards")
_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS llm_cache (key TEXT PRIMARY KEY, response TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS budget (day TEXT, owner TEXT, model TEXT, cost_rub REAL, tokens_in INT, tokens_out INT);
CREATE TABLE IF NOT EXISTS traces (trace_id TEXT, ts TEXT, step TEXT, body TEXT);
CREATE INDEX IF NOT EXISTS traces_id ON traces(trace_id);
""" + "".join(f"CREATE TABLE IF NOT EXISTS {t} (id TEXT PRIMARY KEY, body TEXT);\n" for t in DOC_TABLES)


def db_path() -> Path:
    p = settings().db_path
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


@contextmanager
def conn() -> Iterator[sqlite3.Connection]:
    with _lock:
        c = sqlite3.connect(db_path())
        try:
            c.executescript(SCHEMA)
            yield c
            c.commit()
        finally:
            c.close()


def put(table: str, id_: str, obj: BaseModel) -> None:
    assert table in DOC_TABLES
    with conn() as c:
        c.execute(f"INSERT OR REPLACE INTO {table}(id, body) VALUES (?, ?)", (id_, obj.model_dump_json()))


def put_many(table: str, items: list[tuple[str, BaseModel]]) -> None:
    assert table in DOC_TABLES
    with conn() as c:
        c.executemany(
            f"INSERT OR REPLACE INTO {table}(id, body) VALUES (?, ?)",
            [(i, o.model_dump_json()) for i, o in items],
        )


def get(table: str, id_: str, model: type[T]) -> T | None:
    with conn() as c:
        row = c.execute(f"SELECT body FROM {table} WHERE id = ?", (id_,)).fetchone()
    return model.model_validate_json(row[0]) if row else None


def all_(table: str, model: type[T]) -> list[T]:
    with conn() as c:
        rows = c.execute(f"SELECT body FROM {table} ORDER BY id").fetchall()
    return [model.model_validate_json(r[0]) for r in rows]


def clear(table: str) -> None:
    with conn() as c:
        c.execute(f"DELETE FROM {table}")


def raw(sql: str, params: tuple = ()) -> list[tuple]:
    with conn() as c:
        return c.execute(sql, params).fetchall()


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)
