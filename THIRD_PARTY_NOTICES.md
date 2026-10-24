# Third-party notices

Перечень собран из установленного окружения (`uv sync`) 23.10.2026. Обновлять при добавлении зависимостей:
`uv run python scripts/licenses.py` (TODO D) или вручную по `uv.lock`.

## Runtime

| Пакет | Версия | Лицензия |
| --- | --- | --- |
| fastapi | 0.162.0 | MIT |
| starlette | 1.9.0 | BSD-3-Clause |
| uvicorn | 0.54.0 | BSD-3-Clause |
| pydantic / pydantic_core | 2.14.1 / 2.50.1 | MIT |
| pyyaml | 6.0.3 | MIT |
| httpx / httpcore | 0.28.1 / 1.0.9 | BSD-3-Clause |
| snowballstemmer | 3.1.1 | BSD-3-Clause |
| anyio | 4.15.1 | MIT |
| h11 | 0.16.0 | MIT |
| idna | 3.20 | BSD-3-Clause |
| certifi | 2026.10.23 | MPL-2.0 |
| click | 8.5.0 | BSD-3-Clause |
| annotated-doc, annotated-types, typing-inspection | — | MIT |
| typing_extensions | 4.16.0 | PSF-2.0 |
| opentelemetry-api | 1.45.1 | Apache-2.0 |

## Опциональные

| Пакет | Лицензия | Зачем |
| --- | --- | --- |
| pypdf | BSD-3-Clause | нарезка PDF материалов банка (`uv sync --extra pdf`) |
| numpy | BSD-3-Clause | векторы эмбеддингов (`--extra embeddings`) |

PyMuPDF не используется намеренно: лицензия AGPL-3.0.

## Dev

pytest (MIT), pluggy (MIT), iniconfig (MIT), packaging (Apache-2.0 OR BSD-2-Clause), pygments (BSD-2-Clause), ruff (MIT).

## Модели

Используются только модели, разрешённые условиями кейса: Gemma 4 26B A4B, GLM-5.3-Flash, Qwen3.6 35B A3B,
DeepSeek-V4.1-Flash, Qwen3-VL-30B-A3B-Instruct, Kimi-K2.6 — через API организаторов. Лицензии моделей — у правообладателей.

## Идеи

Архитектурные идеи (структурированный вывод с guardrail и повтором, хуки инструментов, шина событий, Flow-состояние)
взяты из CrewAI (MIT, https://github.com/crewAIInc/crewAI) и реализованы заново; код CrewAI не используется.
