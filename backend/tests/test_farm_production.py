def test_create_farm_production(auth_client, test_cooperative):
    """POST /production/farm creates a farm production record."""
    res = auth_client.post(
        f"/production/farm/?cooperative_id={test_cooperative.id}",
        json={
            "crop_type": "Maize",
            "season": "2026A",
            "planted_date": "2026-03-15",
            "expected_quantity_kg": 500.0,
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["crop_type"] == "Maize"
    assert data["season"] == "2026A"
    assert data["expected_quantity_kg"] == 500.0
    assert data["cooperative_id"] == test_cooperative.id


def test_list_farm_production(auth_client, test_cooperative):
    """GET /production/farm lists farm production records."""
    auth_client.post(
        f"/production/farm/?cooperative_id={test_cooperative.id}",
        json={
            "crop_type": "Soybeans",
            "season": "2026B",
            "planted_date": "2026-06-01",
            "expected_quantity_kg": 300.0,
        },
    )
    res = auth_client.get(f"/production/farm/?cooperative_id={test_cooperative.id}")
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_update_farm_production(auth_client, test_cooperative):
    """PATCH /production/farm/{id} updates a record."""
    created = auth_client.post(
        f"/production/farm/?cooperative_id={test_cooperative.id}",
        json={
            "crop_type": "Cassava",
            "season": "2026A",
            "planted_date": "2026-02-10",
            "expected_quantity_kg": 800.0,
        },
    ).json()
    res = auth_client.patch(
        f"/production/farm/{created['id']}?cooperative_id={test_cooperative.id}",
        json={"actual_quantity_kg": 750.0, "quality_grade": "A"},
    )
    assert res.status_code == 200
    assert res.json()["actual_quantity_kg"] == 750.0
    assert res.json()["quality_grade"] == "A"


def test_cross_coop_not_found(auth_client, test_cooperative, another_cooperative):
    """Records from one cooperative are not visible to another."""
    auth_client.post(
        f"/production/farm/?cooperative_id={test_cooperative.id}",
        json={
            "crop_type": "Sorghum",
            "season": "2026A",
            "planted_date": "2026-04-01",
            "expected_quantity_kg": 200.0,
        },
    )
    res = auth_client.get(f"/production/farm/?cooperative_id={another_cooperative.id}")
    assert res.status_code == 200
    assert len(res.json()) == 0
