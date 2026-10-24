from app.agent import checks
from app.agent.flow import build_card
from app.llm import trace
from contracts.models import CardDraft, Claim, Source


def test_card_end_to_end_mock():
    card = build_card("U001", "n003", refresh=True)
    assert card.what_happened and card.why_it_matters and card.actions
    ids = {s.source_id for s in card.sources}
    for block in checks.BLOCKS:
        for c in getattr(card, block):
            assert set(c.source_ids) <= ids
    assert card.self_check.passed
    steps = [e.step for e in trace.get(card.trace_id)]
    assert "agent.plan" in steps and "agent.draft" in steps and "agent.judge" in steps


def test_card_is_cached():
    a = build_card("U002", "n010")
    b = build_card("U002", "n010")
    assert a.trace_id == b.trace_id


def test_static_checks_catch_bad_claims():
    pool = {
        "news:n1": Source(source_id="news:n1", type="news", ref="u", quote="Ставка 14%"),
        "profile:key_rate": Source(
            source_id="profile:key_rate", type="profile", ref="e", quote="есть кредит"
        ),
    }
    d = CardDraft(
        what_happened=[Claim(text="Ставка выросла до 16%", kind="fact", source_ids=["news:n1"])],
        why_it_matters=[Claim(text="Важно", kind="bank", source_ids=["profile:key_rate"])],
        actions=[Claim(text="Сделать", kind="ai", source_ids=["nope"])],
    )
    issues = checks.static(d, pool, {})
    text = " ".join(issues)
    assert "16" in text and "kind=bank" in text and "несуществующие" in text
    cleaned, dropped = checks.drop_unsupported(d, pool, {}, set())
    assert len(dropped) == 3 and cleaned.what_happened  # обязательный блок восстановлен из новости
