def register_customer(
    client,
    username: str = "customer_one",
    email: str = "customer_one@example.com",
    password: str = "SecurePassword123!",
):
    response = client.post(
        "/users",
        json={
            "username": username,
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 201
    return response.json()


def login_headers(
    client,
    username: str = "customer_one",
    password: str = "SecurePassword123!",
):
    response = client.post(
        "/auth/login",
        data={
            "username": username,
            "password": password,
        },
    )

    assert response.status_code == 200

    access_token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {access_token}",
    }


def create_customer_and_headers(client):
    register_customer(client)

    return login_headers(client)


def test_create_ticket(client):
    headers = create_customer_and_headers(client)

    payload = {
        "subject": "I was charged twice for order ORD-1042",
        "description": "My card shows two successful payments for the same order.",
    }

    response = client.post(
        "/tickets",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 201

    body = response.json()

    assert body["id"] == 1
    assert body["subject"] == payload["subject"]
    assert body["description"] == payload["description"]
    assert body["status"] == "OPEN"


def test_create_ticket_rejects_invalid_input(client):
    headers = create_customer_and_headers(client)

    payload = {
        "subject": "Bad",
        "description": "short",
    }

    response = client.post(
        "/tickets",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 422


def test_get_missing_ticket_returns_404(client):
    headers = create_customer_and_headers(client)

    response = client.get(
        "/tickets/999999",
        headers=headers,
    )

    assert response.status_code == 404