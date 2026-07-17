"""Tests for /production endpoints"""

from app.models.models import CooperativeMembership, Production


def test_unified_production_columns_have_migration_compatible_defaults():
    membership_columns = CooperativeMembership.__table__.c
    production_columns = Production.__table__.c

    assert membership_columns.production_focus.server_default.arg == "crop"
    assert membership_columns.production_focus.nullable is False
    assert production_columns.production_kind.server_default.arg == "crop"
    assert production_columns.production_kind.nullable is False
    assert production_columns.unit.server_default.arg == "kg"
    assert production_columns.unit.nullable is False
    assert production_columns.crop_type.nullable is True


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
    assert data["production_kind"] == "crop"
    assert data["product_name"] == "Cocoa"
    assert data["unit"] == "kg"
    assert data["expected_quantity"] == 1000.0
    assert data["production_date"] == "2025-01-15T00:00:00"
    assert data["harvest_date"] is None


def test_create_production_bad_farmer(client):
    resp = client.post(
        "/production/",
        json={"farmer_id": 999999, "crop_type": "Maize"},
    )
    assert resp.status_code == 404


def test_list_productions(client, farmer, cooperative):
    client.post(
        "/production/",
        json={"farmer_id": farmer["id"], "crop_type": "Cassava"},
    )
    resp = client.get(f"/production/?cooperative_id={cooperative['id']}")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_list_productions_requires_cooperative_scope(client):
    resp = client.get("/production/")
    assert resp.status_code == 400


def test_list_productions_filter_by_crop(client, farmer, cooperative):
    client.post("/production/", json={"farmer_id": farmer["id"], "crop_type": "Yam"})
    resp = client.get(f"/production/?cooperative_id={cooperative['id']}&crop_type=yam")
    assert resp.status_code == 200
    assert all("yam" in p["crop_type"].lower() for p in resp.json())


def test_animal_production_validation_filter_and_summary(client, cooperative):
    member_response = client.post(
        "/farmers/",
        json={
            "name": "Esi Layers",
            "phone": "+233551000066",
            "cooperative_id": cooperative["id"],
            "production_focus": "animal",
            "animal_type": "Layers",
            "animal_scale": 400,
        },
    )
    member = member_response.json()

    rejected_crop = client.post(
        "/production/",
        json={"farmer_id": member["id"], "crop_type": "Maize"},
    )
    assert rejected_crop.status_code == 422

    created = client.post(
        "/production/",
        json={
            "farmer_id": member["id"],
            "production_kind": "animal",
            "product_name": "Eggs",
            "activity": "collection",
            "unit": "crates",
            "expected_quantity": 12,
            "quantity": 10,
            "production_date": "2026-07-16T00:00:00",
        },
    )
    assert created.status_code == 201, created.text
    record = created.json()
    assert record["crop_type"] is None
    assert record["product_name"] == "Eggs"
    assert record["quantity"] == 10
    assert record["quantity_kg"] is None

    filtered = client.get(
        f"/production/?cooperative_id={cooperative['id']}"
        "&production_kind=animal&product_name=egg"
    )
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()] == [record["id"]]

    summary = client.get(f"/production/farmer/{member['id']}/summary")
    assert summary.status_code == 200
    assert summary.json()["completed_productions"] == 1
    assert summary.json()["totals_by_unit"] == {"crates": 10.0}
    assert summary.json()["production_completion_rate"] == 100.0


def test_mixed_member_accepts_both_production_kinds(client, cooperative):
    member = client.post(
        "/farmers/",
        json={
            "name": "Yaw Mixed",
            "phone": "+233551000067",
            "cooperative_id": cooperative["id"],
            "production_focus": "mixed",
            "crop_type": "Maize",
            "animal_type": "Goats",
        },
    ).json()
    crop = client.post(
        "/production/",
        json={"farmer_id": member["id"], "crop_type": "Maize"},
    )
    animal = client.post(
        "/production/",
        json={
            "farmer_id": member["id"],
            "production_kind": "animal",
            "product_name": "Goats",
            "activity": "births",
            "unit": "head",
        },
    )
    assert crop.status_code == 201, crop.text
    assert animal.status_code == 201, animal.text


def test_crop_member_rejects_animal_production(client, farmer):
    response = client.post(
        "/production/",
        json={
            "farmer_id": farmer["id"],
            "production_kind": "animal",
            "product_name": "Milk",
            "unit": "litres",
        },
    )
    assert response.status_code == 422


def test_rejects_kg_aliases_for_non_kg_units(client, cooperative):
    member = client.post(
        "/farmers/",
        json={
            "name": "Kwame Unit",
            "phone": "+233551000068",
            "cooperative_id": cooperative["id"],
            "production_focus": "animal",
            "animal_type": "Cattle",
        },
    ).json()
    response = client.post(
        "/production/",
        json={
            "farmer_id": member["id"],
            "production_kind": "animal",
            "product_name": "Milk",
            "unit": "litres",
            "expected_kg": 40,
        },
    )
    assert response.status_code == 422


def test_update_clears_stale_crop_and_kg_aliases_for_animal(client, cooperative):
    member = client.post(
        "/farmers/",
        json={
            "name": "Ama Switch",
            "phone": "+233551000069",
            "cooperative_id": cooperative["id"],
            "production_focus": "mixed",
            "crop_type": "Maize",
            "animal_type": "Goats",
        },
    ).json()
    created = client.post(
        "/production/",
        json={
            "farmer_id": member["id"],
            "crop_type": "Maize",
            "expected_kg": 100,
            "quantity_kg": 90,
        },
    )
    assert created.status_code == 201, created.text
    prod_id = created.json()["id"]

    updated = client.put(
        f"/production/{prod_id}",
        json={
            "production_kind": "animal",
            "product_name": "Goats",
            "activity": "sales",
            "unit": "head",
            "expected_quantity": 5,
            "quantity": 4,
        },
    )
    assert updated.status_code == 200, updated.text
    data = updated.json()
    assert data["production_kind"] == "animal"
    assert data["crop_type"] is None
    assert data["expected_kg"] is None
    assert data["quantity_kg"] is None
    assert data["expected_quantity"] == 5
    assert data["quantity"] == 4
    assert data["unit"] == "head"


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
