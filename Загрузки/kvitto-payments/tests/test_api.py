import pytest

from app.models import Payment


def create(client, headers=None, **overrides):
    body = {"tariff_id": "standard", "email": "a@b.ru", "method": "card", **overrides}
    return client.post("/payments", json=body, headers=headers)


def test_list_tariffs(client):
    r = client.get("/tariffs")
    assert r.status_code == 200
    assert {t["id"]: t["price"] for t in r.json()} == {
        "basic": 990_000,
        "standard": 1_990_000,
        "premium": 2_990_000,
    }


def test_amount_without_promo(client):
    r = create(client)
    assert r.status_code == 201
    data = r.json()
    assert data["amount"] == 1_990_000
    assert data["discount"] == 0
    assert data["status"] == "pending"
    assert data["schedule"] is None


@pytest.mark.parametrize("code", ["KVITTO10", "kvitto10"])
def test_amount_with_promo_any_case(client, code):
    data = create(client, promo_code=code).json()
    assert data["discount"] == 199_000
    assert data["amount"] == 1_791_000


def test_unknown_promo_is_422(client):
    assert create(client, promo_code="NOPE").status_code == 422


@pytest.mark.parametrize("months", [3, 6, 12])
@pytest.mark.parametrize("promo", [None, "KVITTO10"])
def test_installment_schedule_sums_to_amount(client, months, promo):
    data = create(
        client, method="installment", installment_months=months, promo_code=promo
    ).json()
    assert len(data["schedule"]) == months
    assert sum(data["schedule"]) == data["amount"]


def test_installment_example_from_task(client):
    data = create(client, method="installment", installment_months=3).json()
    assert data["schedule"] == [663_334, 663_333, 663_333]


@pytest.mark.parametrize("months", [None, 5, 0])
def test_installment_requires_valid_months(client, months):
    r = create(client, method="installment", installment_months=months)
    assert r.status_code == 422


def test_idempotency_key_does_not_create_duplicate(client, session_factory):
    headers = {"Idempotency-Key": "key-1"}
    first = create(client, headers=headers)
    second = create(client, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    with session_factory() as db:
        assert db.query(Payment).count() == 1


def test_different_idempotency_keys_create_different_payments(client):
    a = create(client, headers={"Idempotency-Key": "a"}).json()
    b = create(client, headers={"Idempotency-Key": "b"}).json()
    assert a["id"] != b["id"]


def test_get_payment(client):
    created = create(client).json()
    r = client.get(f"/payments/{created['id']}")
    assert r.status_code == 200
    assert r.json() == created


def test_get_missing_payment_is_404(client):
    assert client.get("/payments/999").status_code == 404


def test_webhook_valid_transition(client):
    pid = create(client).json()["id"]
    r = client.post("/webhooks/bank", json={"payment_id": pid, "status": "succeeded"})
    assert r.status_code == 200
    assert r.json() == {"result": "ok"}
    assert client.get(f"/payments/{pid}").json()["status"] == "succeeded"


def test_webhook_forbidden_transition_is_409_and_status_unchanged(client):
    pid = create(client).json()["id"]
    # pending -> refunded запрещён
    r = client.post("/webhooks/bank", json={"payment_id": pid, "status": "refunded"})
    assert r.status_code == 409
    assert r.json() == {"error": "invalid_transition"}
    assert client.get(f"/payments/{pid}").json()["status"] == "pending"


def test_webhook_after_failed_is_forbidden(client):
    pid = create(client).json()["id"]
    client.post("/webhooks/bank", json={"payment_id": pid, "status": "failed"})
    r = client.post("/webhooks/bank", json={"payment_id": pid, "status": "succeeded"})
    assert r.status_code == 409
    assert client.get(f"/payments/{pid}").json()["status"] == "failed"


def test_webhook_missing_payment_is_404(client):
    r = client.post("/webhooks/bank", json={"payment_id": 999, "status": "succeeded"})
    assert r.status_code == 404
