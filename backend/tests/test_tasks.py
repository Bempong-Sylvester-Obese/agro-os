def test_create_task(auth_client, test_cooperative):
    """POST /tasks creates a task."""
    res = auth_client.post(
        f"/tasks/?cooperative_id={test_cooperative.id}",
        json={"title": "Plant maize", "task_type": "planting", "scheduled_date": "2026-08-01"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Plant maize"
    assert data["status"] == "open"
    assert data["task_type"] == "planting"


def test_create_task_with_workers(auth_client, test_cooperative, db):
    """POST /tasks with worker_ids creates assignments."""
    from app.models.work_task import WorkerAssignment

    worker = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Task Worker", "phone": "0241112240"},
    ).json()
    res = auth_client.post(
        f"/tasks/?cooperative_id={test_cooperative.id}",
        json={
            "title": "Weeding", "task_type": "weeding",
            "scheduled_date": "2026-08-05",
            "worker_ids": [worker["id"]],
        },
    )
    assert res.status_code == 201
    assert len(res.json()["assignments"]) == 1
    assignment = (
        db.query(WorkerAssignment)
        .filter(WorkerAssignment.work_task_id == res.json()["id"])
        .one()
    )
    assert assignment.cooperative_id == test_cooperative.id


def test_list_tasks(auth_client, test_cooperative):
    """GET /tasks lists tasks."""
    auth_client.post(
        f"/tasks/?cooperative_id={test_cooperative.id}",
        json={"title": "Harvest", "task_type": "harvesting", "scheduled_date": "2026-08-10"},
    )
    res = auth_client.get(f"/tasks/?cooperative_id={test_cooperative.id}")
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_update_task_status(auth_client, test_cooperative):
    """PATCH /tasks/{id} updates status."""
    created = auth_client.post(
        f"/tasks/?cooperative_id={test_cooperative.id}",
        json={"title": "Irrigate", "task_type": "irrigation", "scheduled_date": "2026-08-15"},
    ).json()
    res = auth_client.patch(
        f"/tasks/{created['id']}?cooperative_id={test_cooperative.id}",
        json={"status": "in_progress"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "in_progress"


def test_assign_workers_to_task(auth_client, test_cooperative):
    """POST /tasks/{id}/assign adds worker assignments."""
    task = auth_client.post(
        f"/tasks/?cooperative_id={test_cooperative.id}",
        json={"title": "Fertilize", "task_type": "fertilizing", "scheduled_date": "2026-08-20"},
    ).json()
    worker = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Assign Me", "phone": "0241112241"},
    ).json()
    res = auth_client.post(
        f"/tasks/{task['id']}/assign?cooperative_id={test_cooperative.id}",
        json={"worker_ids": [worker["id"]]},
    )
    assert res.status_code == 200
    assert len(res.json()["assignments"]) == 1


def test_task_cross_coop_not_found(auth_client, test_cooperative, another_cooperative):
    auth_client.post(
        f"/tasks/?cooperative_id={test_cooperative.id}",
        json={"title": "Secret", "task_type": "general", "scheduled_date": "2026-09-01"},
    )
    res = auth_client.get(f"/tasks/?cooperative_id={another_cooperative.id}")
    assert res.status_code == 200
    assert len(res.json()) == 0


def test_create_task_rejects_cross_tenant_worker(
    auth_client, test_cooperative, another_cooperative
):
    foreign_worker = auth_client.post(
        f"/workers/?cooperative_id={another_cooperative.id}",
        json={"name": "Foreign Worker", "phone": "0241112299"},
    ).json()
    res = auth_client.post(
        f"/tasks/?cooperative_id={test_cooperative.id}",
        json={
            "title": "Should fail",
            "task_type": "general",
            "scheduled_date": "2026-09-02",
            "worker_ids": [foreign_worker["id"]],
        },
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "One or more workers not found"


def test_assign_workers_rejects_cross_tenant_worker(
    auth_client, test_cooperative, another_cooperative
):
    task = auth_client.post(
        f"/tasks/?cooperative_id={test_cooperative.id}",
        json={"title": "Local task", "task_type": "general", "scheduled_date": "2026-09-03"},
    ).json()
    foreign_worker = auth_client.post(
        f"/workers/?cooperative_id={another_cooperative.id}",
        json={"name": "Other Coop Worker", "phone": "0241112298"},
    ).json()
    res = auth_client.post(
        f"/tasks/{task['id']}/assign?cooperative_id={test_cooperative.id}",
        json={"worker_ids": [foreign_worker["id"]]},
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "One or more workers not found"
