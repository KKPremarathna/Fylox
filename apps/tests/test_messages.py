def register_customer(client, username, email):
    response = client.post(
        "/users",
        json={
            "username": username,
            "email": email,
            "password": "SecurePassword123!",
        },
    )
    assert response.status_code == 201


def login_headers(client, username):
    response = client.post(
        "/auth/login",
        data={
            "username": username,
            "password": "SecurePassword123!",
        },
    )
    assert response.status_code == 200

    return {
        "Authorization": (
            f"Bearer {response.json()['access_token']}"
        )
    }


def test_customer_message_creates_activity(client):
    register_customer(
        client,
        username="message_customer",
        email="message_customer@example.com",
    )

    headers = login_headers(client, username="message_customer")

    ticket_response = client.post(
        "/tickets",
        json={
            "subject": "Payment issue on my account",
            "description": "A payment appears twice on my statement.",
        },
        headers=headers,
    )
    assert ticket_response.status_code == 201

    ticket_id = ticket_response.json()["id"]

    message_response = client.post(
        f"/tickets/{ticket_id}/messages",
        json={
            "content": "The duplicate charge was made today.",
        },
        headers=headers,
    )
    assert message_response.status_code == 201
    assert message_response.json()["sender_type"] == "CUSTOMER"

    activity_response = client.get(
        f"/tickets/{ticket_id}/activity",
        headers=headers,
    )
    assert activity_response.status_code == 200

    activity = activity_response.json()

    assert any(
        item["event_type"] == "MESSAGE_CREATED"
        and item["message"] == "Customer added a message."
        for item in activity
    )