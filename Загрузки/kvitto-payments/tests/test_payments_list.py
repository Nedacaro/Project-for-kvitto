def set_status(client, payment_id, status):
    r = client.post("/webhooks/bank", json={"payment_id": payment_id, "status": status})
    assert r.status_code == 200


def test_list_without_filters_returns_all(client, make_payment):
    a = make_payment(email="a@b.ru")
    b = make_payment(email="c@d.ru")
    r = client.get("/payments")
    assert r.status_code == 200
    assert [p["id"] for p in r.json()] == [a["id"], b["id"]]


def test_filter_by_email_ignores_case(client, make_payment):
    a = make_payment(email="a@b.ru")
    make_payment(email="c@d.ru")
    r = client.get("/payments", params={"email": "A@B.RU"})
    assert [p["id"] for p in r.json()] == [a["id"]]


def test_filter_by_status(client, make_payment):
    first = make_payment()
    make_payment()
    set_status(client, first["id"], "succeeded")
    r = client.get("/payments", params={"status": "succeeded"})
    assert [p["id"] for p in r.json()] == [first["id"]]


def test_filter_by_email_and_status(client, make_payment):
    a = make_payment(email="a@b.ru")
    b = make_payment(email="c@d.ru")
    set_status(client, a["id"], "succeeded")
    set_status(client, b["id"], "succeeded")
    r = client.get("/payments", params={"email": "a@b.ru", "status": "succeeded"})
    assert [p["id"] for p in r.json()] == [a["id"]]


def test_filter_returns_empty_list_when_nothing_matches(client, make_payment):
    make_payment(email="a@b.ru")
    assert client.get("/payments", params={"email": "nobody@x.ru"}).json() == []


def test_unknown_status_is_422(client):
    assert client.get("/payments", params={"status": "weird"}).status_code == 422
