from app.profiles import build as profiles
from app.ranking import feed as ranking


def test_profiles_have_exposures_with_reasons(ingested):
    ps = profiles.all_profiles()
    assert len(ps) == ingested["profiles"]["companies"] == 6
    for p in ps:
        assert p.exposures, p.company_id
        assert all(e.why and e.evidence for e in p.exposures)


def test_profiles_are_diverse(ingested):
    rep = ingested["profiles"]
    assert rep["largest_same_set_share"] < 0.5


def test_feed_is_personal():
    tops = {cid: [r.news_id for r in ranking.feed(cid, 3)] for cid in ("U001", "U002", "U003")}
    assert len({tuple(v) for v in tops.values()}) == 3, tops


def test_feed_has_reasons_and_no_duplicate_events():
    from app.news import pipeline as news

    tags = news.all_tags()
    feed = ranking.feed("U004", 20)
    assert all(r.reasons for r in feed)
    clusters = [tags[r.news_id].cluster_id for r in feed]
    assert len(clusters) == len(set(clusters))


def test_grain_trader_sees_grain_news_first():
    top = ranking.feed("U001", 3)
    from app.news import pipeline as news

    assert any(
        "зерн" in news.get(r.news_id).text.lower() or "пшениц" in news.get(r.news_id).text.lower()
        for r in top
    )
