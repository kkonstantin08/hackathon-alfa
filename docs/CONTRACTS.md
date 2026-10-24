# Контракты приложения: текущий скелет

Это реестр прочитанного кода alfa-news.zip. Подтверждение потребителями и окончательная фиксация входят в C-01. Документ не доказывает готовность всех функций.

Взаимодействие AI-агентов описано отдельно в [AGENT_CONTRACT.md](AGENT_CONTRACT.md).

| ID | Производитель | Публичный интерфейс | Типы | Потребители |
| --- | --- | --- | --- | --- |
| APP-01 | A, app/profiles/build.py | build(companies_csv, payments_csv=None), save, get(company_id), all_profiles | CompanyProfile, Exposure, Counterparty | ranking A; agent/API C; frontend через API D |
| APP-02 | B, app/news/pipeline.py | load, tag, dedup, save, get, tags, all_news, all_tags, related | NewsItem, NewsTags | ranking A; agent C |
| APP-03 | B, app/bank_kb/kb.py | load_chunks, chunk_pdf, save, search(query, factors=None, k=5) | BankSnippet | tools/agent C |
| APP-04 | A, app/ranking/feed.py | feed(company_id, k=20) | list[RankedNews] | API C; frontend D |
| APP-05 | C, app/llm/gateway.py | call_structured(alias, messages, schema, validators, max_retries, temperature, step) | Pydantic result, BudgetExceeded, LLMFailed | news B; agent/chat C |
| APP-06 | C, app/agent/flow.py | build_card(company_id, news_id, refresh=False) | AnalysisCard, SelfCheck, Source | API C; frontend D |
| APP-07 | C, app/agent/chat.py | chat(card_id, message, history=None) | ChatAnswer и trace_id | API C; frontend D |

Сигнатуры и типы берутся из исходников; параметры validators и далее у call_structured именованные. Поля и ограничения — contracts/models.py, ID факторов — contracts/factors.yaml. Не поддерживать независимые скопированные версии схем.

## HTTP API

| Метод и путь | Вход | Ответ скелета |
| --- | --- | --- |
| GET /api/health | — | ok, llm_mode, spent_today_rub, daily_budget_rub |
| GET /api/companies | — | list[CompanyBrief] |
| GET /api/companies/{company_id} | company_id | CompanyProfile |
| GET /api/feed | company_id, k | list[RankedNews] |
| GET /api/cards/{company_id}/{news_id} | ID, refresh | AnalysisCard |
| POST /api/chat | card_id, message, history | answer: ChatAnswer, trace_id |
| GET /api/trace/{trace_id} | trace_id | list[TraceEvent] |

API принадлежит C, frontend-потребитель — D. Часть 404/429/502 обработана в скелете; полнота ошибок, параметры, безопасные тела и изоляция контекста проверяются в C-06. Отсутствующий обработчик не считается утверждённой политикой.

Импорт папки PDF, разметка фрагментов и эмбеддинги ещё требуют реализации, даже если упомянуты в docstring или настройках.

## Изменения и подтверждение

1. Назвать Issue, производителей и потребителей, старое и новое поведение.
2. До несовместимого изменения отправить CONTRACT_CHANGE; молчание не считать согласием.
3. Согласовать переход. Даже optional-поле проверять с действительными потребителями.
4. Обновить модели, реестр, примеры и проверки связанных сторон в согласованном PR.
5. Передать точный коммит и способ проверки; отличать ветку от принятого main.

В C-01 нужны валидируемые примеры успешного ответа, пустого результата и ошибки для каждой используемой границы. Команда подтверждает контракт по существующему скелету, не ожидая завершения всех модулей.
