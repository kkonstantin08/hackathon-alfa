"""M1 profiles: CSV клиентов + платежи → CompanyProfile с экспозициями. Без LLM.

Публичное API:
    build(companies_csv, payments_csv=None) -> list[CompanyProfile]
    get(company_id) -> CompanyProfile | None
    all_profiles() -> list[CompanyProfile]
"""

from __future__ import annotations

import csv
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import yaml

from app import store
from app.config import settings
from contracts.models import CompanyProfile, Counterparty, Evidence, Exposure

PRODUCT_COLS = {
    "rko": "CL_PRODUCT_RKO_MARK",
    "gar": "CL_PRODUCT_GAR_MARK",
    "loa": "CL_PRODUCT_LOA_MARK",
    "lea": "CL_PRODUCT_LEA_MARK",
    "dep": "CL_PRODUCT_DEP_MARK",
    "zpp": "CL_PRODUCT_ZPP_MARK",
    "factoring": "FACTORING_MARK",
}
_LEVEL_ORDER = {"low": 0, "medium": 1, "high": 2}


def truthy(v) -> bool:
    """Формат флагов в реальном CSV неизвестен (0/1, Y/N, Да/Нет) — нормализуем всё."""
    return str(v).strip().lower() in {"1", "1.0", "y", "yes", "true", "да", "д"}


@lru_cache
def rules() -> dict:
    return yaml.safe_load((settings().contracts_dir / "exposure_rules.yaml").read_text(encoding="utf-8"))


def _match(cond: dict, row: dict) -> bool:
    for k, v in cond.items():
        if k == "okved_prefix":
            if not str(row.get("MAINOKVED_CODE", "")).startswith(str(v)):
                return False
        elif k == "fts_country_in":
            if row.get("FTS_COUNTRY_NAME") not in v:
                return False
        elif k.endswith("_MARK") or k == "FTS_FLAG":
            if truthy(row.get(k)) != truthy(v):
                return False
        elif str(row.get(k)) != str(v):
            return False
    return True


def _evidence(cond: dict, row: dict) -> list[Evidence]:
    ev = []
    for k in cond:
        field = {"okved_prefix": "MAINOKVED_CODE", "fts_country_in": "FTS_COUNTRY_NAME"}.get(k, k)
        ev.append(Evidence(field=field, value=row.get(field)))
    return ev


def _add(exps: dict[str, Exposure], e: Exposure) -> None:
    """Один фактор — одна экспозиция: берём максимальный уровень, причины склеиваем."""
    old = exps.get(e.factor)
    if old is None:
        exps[e.factor] = e
        return
    level = max(old.level, e.level, key=_LEVEL_ORDER.__getitem__)
    why = old.why if e.why in old.why else f"{old.why}; {e.why}"
    exps[e.factor] = Exposure(factor=e.factor, level=level, why=why, evidence=old.evidence + e.evidence)


def exposures_for(row: dict) -> list[Exposure]:
    r = rules()
    exps: dict[str, Exposure] = {}
    for block in ("products", "foreign_trade", "okved"):
        for rule in r.get(block, []):
            if _match(rule["when"], row):
                _add(
                    exps,
                    Exposure(
                        factor=rule["factor"],
                        level=rule["level"],
                        why=rule["why"],
                        evidence=_evidence(rule["when"], row),
                    ),
                )
    if row.get("REGION") and any(rule for rule in r.get("okved", []) if _match(rule["when"], row)):
        reg = r["regional"]
        _add(
            exps,
            Exposure(
                factor=reg["factor"],
                level=reg["level"],
                why=f"{reg['why']}: {row['REGION']}",
                evidence=[Evidence(field="REGION", value=row["REGION"])],
            ),
        )
    return list(exps.values())


def _read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _counterparties(payments: list[dict], okved: dict[str, str]) -> dict[str, list[Counterparty]]:
    out_amt: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))  # payer → beneficiary
    in_amt: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for p in payments:
        amt = float(p.get("PAY_AMT") or 0)
        out_amt[p["PAYER"]][p["BENEFICIARY"]] += amt
        in_amt[p["BENEFICIARY"]][p["PAYER"]] += amt
    res: dict[str, list[Counterparty]] = defaultdict(list)
    for cid in set(out_amt) | set(in_amt):
        total = sum(out_amt[cid].values()) + sum(in_amt[cid].values()) or 1.0
        for other, amt in out_amt[cid].items():
            res[cid].append(
                Counterparty(
                    company_id=other, okved_code=okved.get(other), share=amt / total, role="supplier"
                )
            )
        for other, amt in in_amt[cid].items():
            res[cid].append(
                Counterparty(company_id=other, okved_code=okved.get(other), share=amt / total, role="buyer")
            )
        res[cid].sort(key=lambda c: -c.share)
    return res


def _counterparty_exposures(cps: list[Counterparty], rows_by_id: dict[str, dict]) -> list[Exposure]:
    """Фактор контрагента с долей ≥ 20% даёт компании экспозицию уровня low."""
    out = []
    for cp in cps:
        if cp.share < 0.2 or cp.company_id not in rows_by_id:
            continue
        row = rows_by_id[cp.company_id]
        for rule in rules().get("okved", []):
            if _match(rule["when"], row):
                who = "поставщик" if cp.role == "supplier" else "покупатель"
                out.append(
                    Exposure(
                        factor=rule["factor"],
                        level="low",
                        why=f"{who} ({rule['why']}) — {cp.share:.0%} оборота",
                        evidence=[Evidence(field="payments", value=f"{cp.company_id}:{cp.share:.2f}")],
                    )
                )
    return out


def build(companies_csv: Path, payments_csv: Path | None = None) -> list[CompanyProfile]:
    rows = _read_csv(companies_csv)
    rows_by_id = {r["SYNTHETIC_U"]: r for r in rows}
    okved = {r["SYNTHETIC_U"]: r.get("MAINOKVED_CODE", "") for r in rows}
    cps = _counterparties(_read_csv(payments_csv), okved) if payments_csv and payments_csv.exists() else {}
    groups: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        if r.get("GROUP_ID"):
            groups[r["GROUP_ID"]].append(r["SYNTHETIC_U"])

    profiles = []
    for r in rows:
        cid = r["SYNTHETIC_U"]
        exps: dict[str, Exposure] = {}
        for e in exposures_for(r) + _counterparty_exposures(cps.get(cid, []), rows_by_id):
            _add(exps, e)
        rev = r.get("REVENUE_COMPANY")
        profiles.append(
            CompanyProfile(
                company_id=cid,
                display_name=f"{r.get('ORG_TYPE', '')} «{r.get('MAINOKVED_NAME', '')[:40]}» ({r.get('CITY', '')})",
                okved_code=r.get("MAINOKVED_CODE", ""),
                okved_name=r.get("MAINOKVED_NAME", ""),
                region=r.get("REGION") or None,
                city=r.get("CITY") or None,
                revenue=float(rev) if rev not in (None, "") else None,
                workers_gradation=r.get("AMOUNT_WORKERS_FNS_GRADATION") or None,
                client_type=r.get("CL_TYPE") or None,
                products={k: truthy(r.get(col)) for k, col in PRODUCT_COLS.items()},
                fts_flag=truthy(r.get("FTS_FLAG")),
                fts_country=r.get("FTS_COUNTRY_NAME") or None,
                group_id=r.get("GROUP_ID") or None,
                group_member_ids=[m for m in groups.get(r.get("GROUP_ID", ""), []) if m != cid],
                counterparties=cps.get(cid, [])[:10],
                exposures=sorted(exps.values(), key=lambda e: -_LEVEL_ORDER[e.level]),
                extra={"negative_mark": r.get("NEGATIVEMARK"), "eco_stage": r.get("ECO_MARK_LABEL")},
            )
        )
    return profiles


def save(profiles: list[CompanyProfile]) -> None:
    store.clear("companies")
    store.put_many("companies", [(p.company_id, p) for p in profiles])


def get(company_id: str) -> CompanyProfile | None:
    return store.get("companies", company_id, CompanyProfile)


def all_profiles() -> list[CompanyProfile]:
    return store.all_("companies", CompanyProfile)


def diversity_report(profiles: list[CompanyProfile]) -> dict:
    """Проверка дня 1: насколько различаются профили. Если почти у всех одинаковые факторы —
    персонализация будет пустой, и это надо знать до того, как строить ранжирование."""
    sigs = defaultdict(int)
    df = defaultdict(int)
    for p in profiles:
        sigs[tuple(sorted(e.factor for e in p.exposures))] += 1
        for e in p.exposures:
            df[e.factor] += 1
    n = len(profiles) or 1
    return {
        "companies": len(profiles),
        "unique_factor_sets": len(sigs),
        "largest_same_set_share": round(max(sigs.values(), default=0) / n, 3),
        "factor_coverage": {f: round(c / n, 3) for f, c in sorted(df.items(), key=lambda x: -x[1])},
        "without_exposures": sum(1 for p in profiles if not p.exposures),
    }
