from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


def test_happy_path():
    assert client.get("/api/health").json()["ok"]
    cs = client.get("/api/companies").json()
    cid = cs[0]["company_id"]
    feed = client.get("/api/feed", params={"company_id": cid}).json()
    assert feed
    nid = feed[0]["news_id"]
    card = client.get(f"/api/cards/{cid}/{nid}").json()
    assert card["what_happened"]
    tr = client.get(f"/api/trace/{card['trace_id']}").json()
    assert len(tr) > 3
    ans = client.post("/api/chat", json={"card_id": card["card_id"], "message": "что делать?"}).json()
    assert "answer" in ans


def test_404s():
    assert client.get("/api/feed", params={"company_id": "nope"}).status_code == 404
    assert client.get("/api/cards/nope/n001").status_code == 404


def test_index_served():
    assert "Новости для бизнеса" in client.get("/").text
