def test_create_worker(auth_client, test_cooperative):
    res = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={
            "name": "John Doe",
            "phone": "0241112233",
            "wage_rate": 50.0,
            "role": "worker",
            "hire_date": "2026-03-01",
            "pay_type": "monthly",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "John Doe"
    assert data["phone"] == "0241112233"
    assert data["wage_rate"] == 50.0
    assert data["status"] == "active"
    assert data["hire_date"] == "2026-03-01"
    assert data["pay_type"] == "monthly"
    assert data["user_id"] is None


def test_create_worker_refused_on_cooperative(auth_client, db):
    from app.models.models import Cooperative

    coop = Cooperative(name="Member Coop", currency="GHS", organization_type="cooperative")
    db.add(coop)
    db.commit()
    res = auth_client.post(
        f"/workers/?cooperative_id={coop.id}",
        json={"name": "Should Fail", "phone": "0241112200", "wage_rate": 20.0},
    )
    assert res.status_code == 403
    assert "solo farm" in res.json()["detail"].lower()


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

    res = auth_client.patch(
        f"/workers/{created['id']}?cooperative_id={test_cooperative.id}",
        json={"hire_date": "2026-01-15", "pay_type": "shift"},
    )
    assert res.status_code == 200
    assert res.json()["hire_date"] == "2026-01-15"
    assert res.json()["pay_type"] == "shift"


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


def test_create_worker_links_same_workspace_user(auth_client, test_cooperative, db):
    from app.models.models import User
    from app.services.auth_service import get_password_hash

    user = User(
        email="linked-supervisor@farm.test",
        hashed_password=get_password_hash("password"),
        role="farm_manager",
        cooperative_id=test_cooperative.id,
    )
    db.add(user)
    db.commit()
    res = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={
            "name": "Linked",
            "phone": "0241112240",
            "user_id": user.id,
        },
    )
    assert res.status_code == 201
    assert res.json()["user_id"] == user.id


def test_create_worker_rejects_foreign_user(auth_client, test_cooperative, another_cooperative, db):
    from app.models.models import User
    from app.services.auth_service import get_password_hash

    user = User(
        email="foreign-supervisor@farm.test",
        hashed_password=get_password_hash("password"),
        role="farm_manager",
        cooperative_id=another_cooperative.id,
    )
    db.add(user)
    db.commit()
    res = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Foreign", "phone": "0241112241", "user_id": user.id},
    )
    assert res.status_code == 403


def test_worker_cap_follows_solo_band(auth_client, db):
    from datetime import datetime, timedelta

    from app.models.models import Cooperative
    from app.models.worker import Worker, WorkerStatus

    coop = Cooperative(
        name="Capped Farm",
        currency="GHS",
        organization_type="solo_farm",
        subscription_plan="solo",
        subscription_band="w20",
        subscription_status="active",
        subscription_expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db.add(coop)
    db.flush()
    for i in range(20):
        db.add(
            Worker(
                cooperative_id=coop.id,
                name=f"Worker {i}",
                phone=f"024200{i:04d}",
                status=WorkerStatus.active,
            )
        )
    db.commit()
    res = auth_client.post(
        f"/workers/?cooperative_id={coop.id}",
        json={"name": "One more", "phone": "0242009999"},
    )
    assert res.status_code == 403
    detail = res.json()["detail"]
    assert detail["code"] == "plan_limit_reached"
    assert detail["limit_key"] == "max_workers"
    assert detail["limit"] == 20


def test_worker_create_blocked_without_worker_module(auth_client, db):
    from app.models.models import Cooperative

    coop = Cooperative(
        name="Starter Farm",
        currency="GHS",
        organization_type="solo_farm",
        subscription_plan="starter",
    )
    db.add(coop)
    db.commit()
    res = auth_client.post(
        f"/workers/?cooperative_id={coop.id}",
        json={"name": "No Plan", "phone": "0242008888"},
    )
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "feature_not_in_plan"


def test_worker_cross_coop_not_found(auth_client, test_cooperative, another_cooperative):
    created = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Cross", "phone": "0241112239"},
    ).json()
    res = auth_client.get(f"/workers/{created['id']}?cooperative_id={another_cooperative.id}")
    assert res.status_code == 404
