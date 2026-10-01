def test_search_expected_query(client, active_refund_policy, db_session):
    res = client.get("/policy-search?query=refund")
    assert res.status_code == 200
    data = res.json()
    assert data["query"] == "refund"
    assert len(data["results"]) > 0
    assert data["results"][0]["document_title"] == "Refund Policy"


def test_search_irrelevant_query(client, active_refund_policy):
    res = client.get("/policy-search?query=cheeseburger")
    assert res.status_code == 200
    assert len(res.json()["results"]) == 0


def test_search_archived_excluded(client, archived_policy):
    res = client.get("/policy-search?query=returns")
    assert res.status_code == 200
    assert len(res.json()["results"]) == 0


def test_public_policies_list_excludes_archived(client, active_refund_policy, archived_policy):
    res = client.get("/policies")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["title"] == "Refund Policy"
    assert "content" not in data[0]


def test_public_get_archived_policy_blocked(client, archived_policy):
    res = client.get(f"/policies/{archived_policy.id}")
    assert res.status_code == 404


def test_customer_cannot_post_policy(customer_client):
    res = customer_client.post("/admin/policies", json={
        "title": "Hacked",
        "version": "v9",
        "content": "Malicious"
    })
    assert res.status_code == 403


def test_admin_can_post_policy(admin_client):
    res = admin_client.post("/admin/policies", json={
        "title": "New Policy",
        "version": "v1.0",
        "content": "# Rule\n\nRule details."
    })
    assert res.status_code == 201
    
    # Needs to be available in public immediately
    pub_res = admin_client.get(f"/policies/{res.json()['id']}")
    assert pub_res.status_code == 200
    assert pub_res.json()["title"] == "New Policy"
