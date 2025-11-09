import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import Base
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="session", autouse=True)
def setup_db(monkeypatch):
    from app import database
    engine = create_engine("sqlite+pysqlite://", future=True, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    database.engine = engine
    database.SessionLocal = TestingSessionLocal
    Base.metadata.create_all(bind=engine)
    yield

@pytest.fixture
def client():
    return TestClient(app)

def test_cache_and_fetch(monkeypatch, client):
    async def fake_fetch(city, units):
        return {"main": {"temp": 20}, "weather": [{"description": "clear"}]}
    monkeypatch.setattr("app.weather_service.fetch_external", fake_fetch)
    r1 = client.post("/weather?city=Oslo&units=metric")
    assert r1.status_code == 200 and r1.json()["from_cache"] is False
    r2 = client.post("/weather?city=Oslo&units=metric")
    assert r2.status_code == 200 and r2.json()["from_cache"] is True

def test_rate_limit(monkeypatch, client):
    from app.main import limiter
    limiter.limit = 2
    async def fake_fetch(city, units):
        return {"main": {"temp": 21}, "weather": [{"description": "ok"}]}
    monkeypatch.setattr("app.weather_service.fetch_external", fake_fetch)
    assert client.post("/weather?city=Riga").status_code == 200
    assert client.post("/weather?city=Riga").status_code == 200
    assert client.post("/weather?city=Riga").status_code == 429

def test_filtering_pagination(monkeypatch, client):
    async def fake_fetch(city, units):
        return {"main": {"temp": 10}, "weather": [{"description": city}]}
    monkeypatch.setattr("app.weather_service.fetch_external", fake_fetch)
    for c in ["London", "Lodz", "Berlin", "Boston"]:
        client.post(f"/weather?city={c}")
    r = client.get("/history?city=lo&per_page=1&page=1")
    js = r.json()
    assert js["per_page"] == 1
    assert js["total"] >= 2
