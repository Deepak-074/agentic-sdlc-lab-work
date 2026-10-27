def _login(client):
    """Register a user and login to get a bearer token."""
    client.post("/users/register", json={
        "username": "testuser",
        "password": "testpassword123"
    })
    response = client.post("/users/login", json={
        "username": "testuser",
        "password": "testpassword123"
    })
    return response.json()["access_token"]


def test_generate_invoice_success(client):
    token = _login(client)

    # Create an order
    order_resp = client.post("/orders/", json={"item": "laptop"}, headers={
        "Authorization": f"Bearer {token}"
    })
    assert order_resp.status_code == 200
    order_data = order_resp.json()
    assert order_data["status"] == "received"
    order_id = order_data["id"]

    # Generate invoice for the order
    invoice_resp = client.post("/payment/generate", json={"order_id": order_id}, headers={
        "Authorization": f"Bearer {token}"
    })
    assert invoice_resp.status_code == 200
    invoice_data = invoice_resp.json()
    assert invoice_data["order_id"] == order_id
    assert invoice_data["status"] == "pending"
    assert invoice_data["external_invoice_id"] is not None

    # Verify order status moved to processing
    order_get = client.get(f"/orders/{order_id}", headers={
        "Authorization": f"Bearer {token}"
    })
    assert order_get.status_code == 200
    assert order_get.json()["status"] == "processing"


def test_generate_invoice_order_not_found(client):
    token = _login(client)
    response = client.post("/payment/generate", json={"order_id": 9999}, headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 404


def test_generate_invoice_already_processing(client):
    token = _login(client)

    order_resp = client.post("/orders/", json={"item": "widget"}, headers={
        "Authorization": f"Bearer {token}"
    })
    order_id = order_resp.json()["id"]

    # Move order to processing manually
    client.put(f"/orders/{order_id}", json={"status": "processing"}, headers={
        "Authorization": f"Bearer {token}"
    })

    # Try to generate invoice - should fail
    response = client.post("/payment/generate", json={"order_id": order_id}, headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 400
    assert "Cannot generate invoice" in response.json()["detail"]


def test_generate_invoice_duplicate(client):
    token = _login(client)

    order_resp = client.post("/orders/", json={"item": "gadget"}, headers={
        "Authorization": f"Bearer {token}"
    })
    order_id = order_resp.json()["id"]

    # Generate first invoice
    client.post("/payment/generate", json={"order_id": order_id}, headers={
        "Authorization": f"Bearer {token}"
    })

    # Try to generate second invoice - order is now PROCESSING, so status check fails first
    response = client.post("/payment/generate", json={"order_id": order_id}, headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 400
    assert "Cannot generate invoice" in response.json()["detail"]


def test_pay_invoice_success(client):
    token = _login(client)

    # Create order and generate invoice
    order_resp = client.post("/orders/", json={"item": "phone"}, headers={
        "Authorization": f"Bearer {token}"
    })
    order_id = order_resp.json()["id"]

    invoice_resp = client.post("/payment/generate", json={"order_id": order_id}, headers={
        "Authorization": f"Bearer {token}"
    })
    invoice_id = invoice_resp.json()["id"]

    # Pay the invoice
    pay_resp = client.post(f"/payment/pay/{order_id}", headers={
        "Authorization": f"Bearer {token}"
    })
    assert pay_resp.status_code == 200
    pay_data = pay_resp.json()
    assert pay_data["status"] == "paid"

    # Verify order status moved to fulfilled
    order_get = client.get(f"/orders/{order_id}", headers={
        "Authorization": f"Bearer {token}"
    })
    assert order_get.status_code == 200
    assert order_get.json()["status"] == "fulfilled"

    # Verify invoice status is paid
    invoice_get = client.get(f"/payment/invoice/{invoice_id}", headers={
        "Authorization": f"Bearer {token}"
    })
    assert invoice_get.status_code == 200
    assert invoice_get.json()["status"] == "paid"


def test_pay_invoice_not_found(client):
    token = _login(client)
    response = client.post("/payment/pay/9999", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 404


def test_get_invoice_by_id(client):
    token = _login(client)

    order_resp = client.post("/orders/", json={"item": "tablet"}, headers={
        "Authorization": f"Bearer {token}"
    })
    order_id = order_resp.json()["id"]

    invoice_resp = client.post("/payment/generate", json={"order_id": order_id}, headers={
        "Authorization": f"Bearer {token}"
    })
    invoice_id = invoice_resp.json()["id"]

    response = client.get(f"/payment/invoice/{invoice_id}", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    assert response.json()["order_id"] == order_id
    assert response.json()["status"] == "pending"


def test_get_invoice_by_order_id(client):
    token = _login(client)

    order_resp = client.post("/orders/", json={"item": "monitor"}, headers={
        "Authorization": f"Bearer {token}"
    })
    order_id = order_resp.json()["id"]

    client.post("/payment/generate", json={"order_id": order_id}, headers={
        "Authorization": f"Bearer {token}"
    })

    response = client.get(f"/payment/invoice/order/{order_id}", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    assert response.json()["order_id"] == order_id


def test_list_invoices(client):
    token = _login(client)

    # Create two orders and generate invoices
    order1 = client.post("/orders/", json={"item": "item1"}, headers={
        "Authorization": f"Bearer {token}"
    }).json()
    client.post("/payment/generate", json={"order_id": order1["id"]}, headers={
        "Authorization": f"Bearer {token}"
    })

    order2 = client.post("/orders/", json={"item": "item2"}, headers={
        "Authorization": f"Bearer {token}"
    }).json()
    client.post("/payment/generate", json={"order_id": order2["id"]}, headers={
        "Authorization": f"Bearer {token}"
    })

    response = client.get("/payment/", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2


def test_payment_without_auth_returns_401(client):
    response = client.get("/payment/")
    assert response.status_code == 401


# -- refund endpoint (issue 4) ----------------------------------------------------

def _paid_order(client, token):
    headers = {"Authorization": f"Bearer {token}"}
    order_id = client.post("/orders/", json={"item": "laptop"}, headers=headers).json()["id"]
    client.post("/payment/generate", json={"order_id": order_id}, headers=headers)
    client.post(f"/payment/pay/{order_id}", headers=headers)
    return order_id, headers


def test_refund_paid_invoice(client):
    token = _login(client)
    order_id, headers = _paid_order(client, token)
    response = client.post(f"/payment/refund/{order_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert client.get(f"/orders/{order_id}", headers=headers).json()["status"] == "cancelled"


def test_refund_pending_invoice_returns_400(client):
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    order_id = client.post("/orders/", json={"item": "laptop"}, headers=headers).json()["id"]
    client.post("/payment/generate", json={"order_id": order_id}, headers=headers)
    assert client.post(f"/payment/refund/{order_id}", headers=headers).status_code == 400


def test_refund_without_invoice_returns_404(client):
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/payment/refund/9999", headers=headers).status_code == 404


def test_refund_shipped_order_returns_400(client):
    token = _login(client)
    order_id, headers = _paid_order(client, token)
    assert client.put(f"/orders/{order_id}", json={"status": "shipped"}, headers=headers).status_code == 200
    response = client.post(f"/payment/refund/{order_id}", headers=headers)
    assert response.status_code == 400
    assert client.get(f"/orders/{order_id}", headers=headers).json()["status"] == "shipped"
