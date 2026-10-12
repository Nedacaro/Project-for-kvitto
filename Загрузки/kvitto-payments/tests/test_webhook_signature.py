import json

import pytest

from app import security

SECRET = "my-secret"


@pytest.fixture()
def with_secret(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", SECRET)


def raw(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode()


def post(client, body: bytes, signature: str | None):
    headers = {"Content-Type": "application/json"}
    if signature is not None:
        headers["X-Signature"] = signature
    return client.post("/webhooks/bank", content=body, headers=headers)


def test_known_signature_value():
    body = b'{"payment_id":1,"status":"succeeded"}'
    assert security.compute_signature(SECRET, body) == (
        "f134654d6b44fac4553a3b1511f13129b4f37c84c9fcd60615005137245b1b49"
    )


def test_valid_signature_is_accepted(client, make_payment, with_secret):
    pid = make_payment()["id"]
    body = raw({"payment_id": pid, "status": "succeeded"})
    r = post(client, body, security.compute_signature(SECRET, body))
    assert r.status_code == 200
    assert r.json() == {"result": "ok"}
    assert client.get(f"/payments/{pid}").json()["status"] == "succeeded"


def test_wrong_signature_is_401_and_status_unchanged(client, make_payment, with_secret):
    pid = make_payment()["id"]
    body = raw({"payment_id": pid, "status": "succeeded"})
    r = post(client, body, "0" * 64)
    assert r.status_code == 401
    assert client.get(f"/payments/{pid}").json()["status"] == "pending"


def test_missing_signature_is_401(client, make_payment, with_secret):
    pid = make_payment()["id"]
    r = post(client, raw({"payment_id": pid, "status": "succeeded"}), None)
    assert r.status_code == 401
    assert client.get(f"/payments/{pid}").json()["status"] == "pending"


def test_signature_of_other_body_is_rejected(client, make_payment, with_secret):
    pid = make_payment()["id"]
    signed_body = raw({"payment_id": pid, "status": "failed"})
    sent_body = raw({"payment_id": pid, "status": "succeeded"})
    r = post(client, sent_body, security.compute_signature(SECRET, signed_body))
    assert r.status_code == 401
    assert client.get(f"/payments/{pid}").json()["status"] == "pending"


def test_without_secret_signature_is_not_required(client, make_payment):
    pid = make_payment()["id"]
    r = post(client, raw({"payment_id": pid, "status": "succeeded"}), None)
    assert r.status_code == 200
