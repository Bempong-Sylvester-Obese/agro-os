def test_log_attendance(auth_client, test_cooperative):
    """POST /attendance logs worker attendance."""
    worker = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Attend Me", "phone": "0241112242"},
    ).json()
    res = auth_client.post(
        f"/attendance/?cooperative_id={test_cooperative.id}",
        json={
            "worker_id": worker["id"],
            "date": "2026-08-01",
            "shift": "morning",
            "hours_worked": 4.0,
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["shift"] == "morning"
    assert data["hours_worked"] == 4.0


def test_list_attendance(auth_client, test_cooperative):
    """GET /attendance lists records for cooperative."""
    worker = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "List Me", "phone": "0241112243"},
    ).json()
    auth_client.post(
        f"/attendance/?cooperative_id={test_cooperative.id}",
        json={"worker_id": worker["id"], "date": "2026-08-02", "shift": "full_day"},
    )
    res = auth_client.get(f"/attendance/?cooperative_id={test_cooperative.id}")
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_attendance_summary(auth_client, test_cooperative):
    """GET /attendance/summary returns aggregated data."""
    worker = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Sum Me", "phone": "0241112244"},
    ).json()
    auth_client.post(
        f"/attendance/?cooperative_id={test_cooperative.id}",
        json={"worker_id": worker["id"], "date": "2026-08-01", "shift": "morning", "hours_worked": 4.0},
    )
    auth_client.post(
        f"/attendance/?cooperative_id={test_cooperative.id}",
        json={"worker_id": worker["id"], "date": "2026-08-02", "shift": "afternoon", "hours_worked": 4.0},
    )
    res = auth_client.get(
        f"/attendance/summary?cooperative_id={test_cooperative.id}"
        f"&period_start=2026-08-01&period_end=2026-08-31"
    )
    assert res.status_code == 200
    assert len(res.json()) >= 1
    summary = next(s for s in res.json() if s["worker_id"] == worker["id"])
    assert summary["total_hours"] == 8.0
    assert summary["total_shifts"] == 2


def test_attendance_filter_by_worker(auth_client, test_cooperative):
    """GET /attendance?worker_id=N filters by worker."""
    w1 = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Filter A", "phone": "0241112245"},
    ).json()
    w2 = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Filter B", "phone": "0241112246"},
    ).json()
    auth_client.post(
        f"/attendance/?cooperative_id={test_cooperative.id}",
        json={"worker_id": w1["id"], "date": "2026-08-03", "shift": "morning"},
    )
    auth_client.post(
        f"/attendance/?cooperative_id={test_cooperative.id}",
        json={"worker_id": w2["id"], "date": "2026-08-03", "shift": "afternoon"},
    )
    res = auth_client.get(f"/attendance/?cooperative_id={test_cooperative.id}&worker_id={w1['id']}")
    assert res.status_code == 200
    assert all(r["worker_id"] == w1["id"] for r in res.json())


def test_log_attendance_rejects_cross_tenant_worker(
    auth_client, test_cooperative, another_cooperative
):
    foreign_worker = auth_client.post(
        f"/workers/?cooperative_id={another_cooperative.id}",
        json={"name": "Foreign Attendance", "phone": "0241112288"},
    ).json()

    res = auth_client.post(
        f"/attendance/?cooperative_id={test_cooperative.id}",
        json={
            "worker_id": foreign_worker["id"],
            "date": "2026-08-04",
            "shift": "morning",
        },
    )

    assert res.status_code == 404
    assert res.json()["detail"] == "Worker not found"


def test_log_attendance_rejects_cross_tenant_task(
    auth_client, test_cooperative, another_cooperative
):
    worker = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Local Attendance", "phone": "0241112287"},
    ).json()
    foreign_task = auth_client.post(
        f"/tasks/?cooperative_id={another_cooperative.id}",
        json={
            "title": "Foreign task",
            "task_type": "general",
            "scheduled_date": "2026-08-04",
        },
    ).json()

    res = auth_client.post(
        f"/attendance/?cooperative_id={test_cooperative.id}",
        json={
            "worker_id": worker["id"],
            "work_task_id": foreign_task["id"],
            "date": "2026-08-04",
            "shift": "morning",
        },
    )

    assert res.status_code == 404
    assert res.json()["detail"] == "Task not found"
