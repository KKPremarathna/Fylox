def register_customer(
    client,
    username: str,
    email: str,
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
    username: str,
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


def create_ticket(
    client,
    headers,
    subject: str = "Private billing issue",
):
    response = client.post(
        "/tickets",
        json={
            "subject": subject,
            "description": "Please investigate this billing issue.",
        },
        headers=headers,
    )

    assert response.status_code == 201
    return response.json()


def test_ticket_owner_can_read_activity(client):
    register_customer(
        client,
        username="customer_one",
        email="customer_one@example.com",
    )

    owner_headers = login_headers(
        client,
        username="customer_one",
    )

    ticket = create_ticket(
        client,
        headers=owner_headers,
    )

    response = client.get(
        f"/tickets/{ticket['id']}/activity",
        headers=owner_headers,
    )

    assert response.status_code == 200
    activity = response.json()

    assert len(activity) == 1
    assert activity[0]["ticket_id"] == ticket["id"]
    assert activity[0]["event_type"] == "TICKET_CREATED"
    assert activity[0]["message"] == "Ticket created."


def test_other_customer_cannot_read_activity(client):
    register_customer(
        client,
        username="customer_one",
        email="customer_one@example.com",
    )

    register_customer(
        client,
        username="customer_two",
        email="customer_two@example.com",
    )

    first_customer_headers = login_headers(
        client,
        username="customer_one",
    )

    second_customer_headers = login_headers(
        client,
        username="customer_two",
    )

    ticket = create_ticket(
        client,
        headers=first_customer_headers,
    )

    response = client.get(
        f"/tickets/{ticket['id']}/activity",
        headers=second_customer_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Not allowed to access this ticket"