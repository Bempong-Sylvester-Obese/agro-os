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


def test_create_task_with_workers(auth_client, test_cooperative):
    """POST /tasks with worker_ids creates assignments."""
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
