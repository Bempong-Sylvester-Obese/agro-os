"""Tests for /farmers endpoints"""


def test_create_farmer(client, cooperative):
    resp = client.post(
        "/farmers/",
        json={
            "name": "Ama Asante",
            "phone": "+233551000010",
            "cooperative_id": cooperative["id"],
            "crop_type": "Cocoa",
            "acreage": 3.0,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Ama Asante"
    assert data["trust_score"] == 0.0
    assert data["membership_status"] == "active"


def test_create_farmer_duplicate_phone(client, farmer):
    resp = client.post(
        "/farmers/",
        json={
            "name": "Duplicate",
            "phone": farmer["phone"],
            "cooperative_id": farmer["cooperative_id"],
        },
    )
    assert resp.status_code == 409


def test_create_farmer_bad_cooperative(client):
    resp = client.post(
        "/farmers/",
        json={
            "name": "Ghost Farmer",
            "phone": "+233000000000",
            "cooperative_id": 99999,
        },
    )
    assert resp.status_code == 404


def test_get_farmer(client, farmer):
    resp = client.get(f"/farmers/{farmer['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == farmer["id"]


def test_get_farmer_not_found(client):
    resp = client.get("/farmers/999999")
    assert resp.status_code == 404


def test_list_farmers(client, farmer):
    resp = client.get("/farmers/")
    assert resp.status_code == 200
    assert any(f["id"] == farmer["id"] for f in resp.json())


def test_list_farmers_filter_cooperative(client, farmer, cooperative):
    resp = client.get(f"/farmers/?cooperative_id={cooperative['id']}")
    assert resp.status_code == 200
    assert all(f["cooperative_id"] == cooperative["id"] for f in resp.json())


def test_update_farmer(client, farmer):
    resp = client.put(
        f"/farmers/{farmer['id']}",
        json={"acreage": 10.0, "crop_type": "Cassava"},
    )
    assert resp.status_code == 200
    assert resp.json()["acreage"] == 10.0
    assert resp.json()["crop_type"] == "Cassava"


def test_deactivate_farmer(client, farmer):
    resp = client.delete(f"/farmers/{farmer['id']}")
    assert resp.status_code == 204

    # Farmer still exists but is inactive
    get_resp = client.get(f"/farmers/{farmer['id']}")
    assert get_resp.json()["membership_status"] == "inactive"


def test_recalculate_trust_score(client, farmer):
    resp = client.post(f"/farmers/{farmer['id']}/recalculate-trust-score")
    assert resp.status_code == 200
    data = resp.json()
    assert "score" in data
    assert 0.0 <= data["score"] <= 100.0


def test_get_trust_score_history(client, farmer):
    # First ensure there's at least one score
    client.post(f"/farmers/{farmer['id']}/recalculate-trust-score")
    resp = client.get(f"/farmers/{farmer['id']}/trust-score/history")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_record_attendance(client, farmer):
    resp = client.post(
        f"/farmers/{farmer['id']}/attendance",
        json={
            "farmer_id": farmer["id"],
            "event_name": "Annual General Meeting",
            "event_date": "2025-06-01T10:00:00",
            "attended": True,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["attended"] is True


def test_list_attendance(client, farmer):
    # Record one first
    client.post(
        f"/farmers/{farmer['id']}/attendance",
        json={
            "farmer_id": farmer["id"],
            "event_name": "Training",
            "event_date": "2025-05-01T09:00:00",
            "attended": False,
        },
    )
    resp = client.get(f"/farmers/{farmer['id']}/attendance")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
