def test_create_worker(auth_client, test_cooperative):
    res = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "John Doe", "phone": "0241112233", "wage_rate": 50.0, "role": "worker"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "John Doe"
    assert data["phone"] == "0241112233"
    assert data["wage_rate"] == 50.0
    assert data["status"] == "active"


def test_list_workers(auth_client, test_cooperative):
    auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Jane", "phone": "0241112234", "wage_rate": 45.0},
    )
    res = auth_client.get(f"/workers/?cooperative_id={test_cooperative.id}")
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_get_worker(auth_client, test_cooperative):
    created = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Bob", "phone": "0241112235", "wage_rate": 55.0},
    ).json()
    res = auth_client.get(f"/workers/{created['id']}?cooperative_id={test_cooperative.id}")
    assert res.status_code == 200
    assert res.json()["name"] == "Bob"


def test_update_worker(auth_client, test_cooperative):
    created = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Alice", "phone": "0241112236", "wage_rate": 40.0},
    ).json()
    res = auth_client.patch(
        f"/workers/{created['id']}?cooperative_id={test_cooperative.id}",
        json={"name": "Alice Updated", "wage_rate": 45.0},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Alice Updated"
    assert res.json()["wage_rate"] == 45.0


def test_delete_worker_soft(auth_client, test_cooperative):
    created = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Charlie", "phone": "0241112237", "wage_rate": 50.0},
    ).json()
    res = auth_client.delete(f"/workers/{created['id']}?cooperative_id={test_cooperative.id}")
    assert res.status_code == 204
    get_res = auth_client.get(f"/workers/{created['id']}?cooperative_id={test_cooperative.id}")
    assert get_res.json()["status"] == "inactive"


def test_create_worker_duplicate_phone(auth_client, test_cooperative):
    auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "First", "phone": "0241112238"},
    )
    res = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Second", "phone": "0241112238"},
    )
    assert res.status_code == 409


def test_worker_cross_coop_not_found(auth_client, test_cooperative, another_cooperative):
    created = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Cross", "phone": "0241112239"},
    ).json()
    res = auth_client.get(f"/workers/{created['id']}?cooperative_id={another_cooperative.id}")
    assert res.status_code == 404
