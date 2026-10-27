def _headers(client, username="history_user"):
    client.post("/users/register", json={"username": username, "password": "testpassword123"})
    token = client.post("/users/login", json={"username": username, "password": "testpassword123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _statuses(client, order_id, headers):
    response = client.get(f"/orders/{order_id}/history", headers=headers)
    assert response.status_code == 200
    return [row["status"] for row in response.json()]


def test_history_records_every_status_change(client):
    headers = _headers(client)
    order_id = client.post("/orders/", json={"item": "laptop"}, headers=headers).json()["id"]
    client.put(f"/orders/{order_id}", json={"status": "processing"}, headers=headers)
    client.put(f"/orders/{order_id}", json={"status": "fulfilled"}, headers=headers)
    client.post(f"/orders/{order_id}/cancel", headers=headers)
    assert _statuses(client, order_id, headers) == ["received", "processing", "fulfilled", "cancelled"]


def test_history_includes_payment_driven_changes(client):
    headers = _headers(client)
    order_id = client.post("/orders/", json={"item": "laptop"}, headers=headers).json()["id"]
    client.post("/payment/generate", json={"order_id": order_id}, headers=headers)
    client.post(f"/payment/pay/{order_id}", headers=headers)
    client.post(f"/payment/refund/{order_id}", headers=headers)
    assert _statuses(client, order_id, headers) == ["received", "processing", "fulfilled", "cancelled"]


def test_history_has_timestamps(client):
    headers = _headers(client)
    order_id = client.post("/orders/", json={"item": "laptop"}, headers=headers).json()["id"]
    rows = client.get(f"/orders/{order_id}/history", headers=headers).json()
    assert len(rows) == 1 and rows[0]["changed_at"]


def test_history_unknown_order_returns_404(client):
    assert client.get("/orders/9999/history", headers=_headers(client)).status_code == 404


def test_history_of_another_users_order_returns_403(client):
    owner = _headers(client, "owner_user")
    other = _headers(client, "other_user")
    order_id = client.post("/orders/", json={"item": "laptop"}, headers=owner).json()["id"]
    assert client.get(f"/orders/{order_id}/history", headers=other).status_code == 403
