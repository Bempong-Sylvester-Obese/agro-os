"""Tests for /production endpoints"""


def test_create_production(client, farmer):
    resp = client.post(
        "/production/",
        json={
            "farmer_id": farmer["id"],
            "crop_type": "Cocoa",
            "season": "2025A",
            "expected_kg": 1000.0,
            "planted_date": "2025-01-15T00:00:00",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["crop_type"] == "Cocoa"
    assert data["harvest_date"] is None


def test_create_production_bad_farmer(client):
    resp = client.post(
        "/production/",
        json={"farmer_id": 999999, "crop_type": "Maize"},
    )
    assert resp.status_code == 404


def test_list_productions(client, farmer):
    client.post("/production/", json={"farmer_id": farmer["id"], "crop_type": "Cassava"})
    resp = client.get("/production/")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_list_productions_filter_by_crop(client, farmer):
    client.post("/production/", json={"farmer_id": farmer["id"], "crop_type": "Yam"})
    resp = client.get("/production/?crop_type=yam")
    assert resp.status_code == 200
    assert all("yam" in p["crop_type"].lower() for p in resp.json())


def test_get_production(client, farmer):
    create_resp = client.post(
        "/production/",
        json={"farmer_id": farmer["id"], "crop_type": "Plantain"},
    )
    prod_id = create_resp.json()["id"]
    resp = client.get(f"/production/{prod_id}")
    assert resp.status_code == 200


def test_update_production(client, farmer):
    create_resp = client.post(
        "/production/",
        json={"farmer_id": farmer["id"], "crop_type": "Cocoa", "expected_kg": 800.0},
    )
    prod_id = create_resp.json()["id"]

    update_resp = client.put(
        f"/production/{prod_id}",
        json={
            "harvest_date": "2025-09-01T00:00:00",
            "quantity_kg": 750.0,
            "quality_grade": "A",
        },
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["quantity_kg"] == 750.0
    assert data["quality_grade"] == "A"
    assert data["harvest_date"] is not None


def test_farmer_production_summary(client, farmer):
    # Create 2 productions, one with harvest
    client.post(
        "/production/",
        json={"farmer_id": farmer["id"], "crop_type": "Cocoa", "expected_kg": 500.0},
    )
    create_resp = client.post(
        "/production/",
        json={"farmer_id": farmer["id"], "crop_type": "Cocoa", "expected_kg": 500.0},
    )
    prod_id = create_resp.json()["id"]
    client.put(
        f"/production/{prod_id}",
        json={"harvest_date": "2025-10-01T00:00:00", "quantity_kg": 450.0},
    )

    resp = client.get(f"/production/farmer/{farmer['id']}/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_productions"] >= 2
    assert data["total_kg_harvested"] >= 450.0
    assert 0.0 <= data["harvest_completion_rate"] <= 100.0


def test_delete_production(client, farmer):
    create_resp = client.post(
        "/production/",
        json={"farmer_id": farmer["id"], "crop_type": "Mango"},
    )
    prod_id = create_resp.json()["id"]
    del_resp = client.delete(f"/production/{prod_id}")
    assert del_resp.status_code == 204


def test_get_farmer_productions(client, farmer):
    client.post("/production/", json={"farmer_id": farmer["id"], "crop_type": "Soy"})
    resp = client.get(f"/production/farmer/{farmer['id']}")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
