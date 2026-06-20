"""Tests for /cooperatives endpoints"""


def test_create_cooperative(client):
    resp = client.post(
        "/cooperatives/",
        json={"name": "Ghana Cocoa Board", "location": "Accra", "currency": "GHS"},
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Ghana Cocoa Board"
    assert resp.json()["currency"] == "GHS"


def test_list_cooperatives(client, cooperative):
    resp = client.get("/cooperatives/")
    assert resp.status_code == 200
    assert any(c["id"] == cooperative["id"] for c in resp.json())


def test_get_cooperative(client, cooperative):
    resp = client.get(f"/cooperatives/{cooperative['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == cooperative["id"]


def test_get_cooperative_not_found(client):
    resp = client.get("/cooperatives/999999")
    assert resp.status_code == 404


def test_update_cooperative(client, cooperative):
    resp = client.put(
        f"/cooperatives/{cooperative['id']}",
        json={"description": "Updated description"},
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated description"


def test_delete_empty_cooperative(client):
    # Create a brand-new cooperative with no farmers
    create_resp = client.post(
        "/cooperatives/",
        json={"name": "Empty Co-op", "currency": "GHS"},
    )
    assert create_resp.status_code == 201
    coop_id = create_resp.json()["id"]

    del_resp = client.delete(f"/cooperatives/{coop_id}")
    assert del_resp.status_code == 204


def test_delete_cooperative_with_farmers_fails(client, cooperative, farmer):
    resp = client.delete(f"/cooperatives/{cooperative['id']}")
    assert resp.status_code == 409
