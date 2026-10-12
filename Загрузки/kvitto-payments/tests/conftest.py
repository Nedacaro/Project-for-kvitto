import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app, seed_tariffs


@pytest.fixture(autouse=True)
def no_webhook_secret(monkeypatch):
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool, 
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as db:
        seed_tariffs(db)
    return factory


@pytest.fixture()
def client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)  
    app.dependency_overrides.clear()


@pytest.fixture()
def make_payment(client):

    def _make(**overrides):
        body = {"tariff_id": "standard", "email": "a@b.ru", "method": "card", **overrides}
        return client.post("/payments", json=body).json()

    return _make
