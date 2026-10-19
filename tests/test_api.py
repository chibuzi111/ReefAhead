"""Integration contract tests using actual generated data/model artifacts."""
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app import app
client=TestClient(app)
@pytest.fixture(scope="module")
def site():
    r=client.get("/api/sites");assert r.status_code==200
    return r.json()[0]["site_id"]
def test_health_and_frontend():
    assert client.get("/health").json()["data_ready"]
    assert "ReefAhead" in client.get("/").text
def test_forecast_export(site):
    r=client.get("/api/forecast",params={"site_id":site,"as_of":"2024-05-15"})
    assert r.status_code==200,r.text
    f=r.json();assert f["issue_date"]=="2024-05-15"
    assert all(p["date"]<="2024-05-15" for p in f["history"])
    assert all(0<=p["lower"]<=p["mean"]<=p["upper"] for p in f["forecasts"])
    assert f["stale_input"]
    csv=client.get("/api/export",params={"site_id":site,"as_of":"2024-05-15"})
    assert csv.status_code==200 and "Research prototype" in csv.text
def test_fail_closed(site):
    assert client.get("/api/forecast",params={"site_id":"unknown"}).status_code==404
    for asof in ["2030-01-01","2010-01-01","nonsense"]:
        assert client.get("/api/forecast",params={"site_id":site,"as_of":asof}).status_code==422
def test_provenance_and_evaluation():
    assert client.get("/api/data-manifest").json()["complete"]
    e=client.get("/api/evaluation").json()
    assert set(e["horizons"])=={"7","14"}
    assert e["horizons"]["7"]["partitions"]["test"]["selected"]["n"]>0
