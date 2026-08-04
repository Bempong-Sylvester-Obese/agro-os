def test_payroll_summary(auth_client, test_cooperative):
    worker = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Pay Worker", "phone": "0241112250", "wage_rate": 50.0},
    ).json()
    auth_client.post(
        f"/attendance/?cooperative_id={test_cooperative.id}",
        json={"worker_id": worker["id"], "date": "2026-09-01", "shift": "morning", "hours_worked": 4.0},
    )
    res = auth_client.get(
        f"/payroll/summary?cooperative_id={test_cooperative.id}&period_start=2026-09-01&period_end=2026-09-30"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_workers"] >= 1
    assert data["total_gross"] >= 0


def test_approve_payroll(auth_client, test_cooperative):
    worker = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Approve Me", "phone": "0241112251", "wage_rate": 45.0},
    ).json()
    auth_client.post(
        f"/attendance/?cooperative_id={test_cooperative.id}",
        json={"worker_id": worker["id"], "date": "2026-09-01", "shift": "full_day", "hours_worked": 8.0},
    )
    res = auth_client.post(
        f"/payroll/approve?cooperative_id={test_cooperative.id}",
        json={"period_start": "2026-09-01", "period_end": "2026-09-30"},
    )
    assert res.status_code == 201
    payouts = res.json()
    assert len(payouts) >= 1
    assert payouts[0]["status"] == "approved"


def test_payroll_history(auth_client, test_cooperative):
    worker = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "History", "phone": "0241112252", "wage_rate": 40.0},
    ).json()
    auth_client.post(
        f"/attendance/?cooperative_id={test_cooperative.id}",
        json={"worker_id": worker["id"], "date": "2026-09-01", "shift": "afternoon", "hours_worked": 4.0},
    )
    auth_client.post(
        f"/payroll/approve?cooperative_id={test_cooperative.id}",
        json={"period_start": "2026-09-01", "period_end": "2026-09-30"},
    )
    res = auth_client.get(f"/payroll/history?cooperative_id={test_cooperative.id}")
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_payroll_duplicate_approve(auth_client, test_cooperative):
    worker = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Duplicate", "phone": "0241112253", "wage_rate": 35.0},
    ).json()
    auth_client.post(
        f"/attendance/?cooperative_id={test_cooperative.id}",
        json={"worker_id": worker["id"], "date": "2026-09-01", "shift": "morning"},
    )
    auth_client.post(
        f"/payroll/approve?cooperative_id={test_cooperative.id}",
        json={"period_start": "2026-09-01", "period_end": "2026-09-30"},
    )
    res = auth_client.post(
        f"/payroll/approve?cooperative_id={test_cooperative.id}",
        json={"period_start": "2026-09-01", "period_end": "2026-09-30"},
    )
    assert res.status_code == 409


def test_disburse_payroll_uses_stable_external_ref(auth_client, test_cooperative, monkeypatch):
    worker = auth_client.post(
        f"/workers/?cooperative_id={test_cooperative.id}",
        json={"name": "Disburse Me", "phone": "0241112254", "wage_rate": 50.0},
    ).json()
    auth_client.post(
        f"/attendance/?cooperative_id={test_cooperative.id}",
        json={"worker_id": worker["id"], "date": "2026-09-01", "shift": "full_day", "hours_worked": 8.0},
    )
    approved = auth_client.post(
        f"/payroll/approve?cooperative_id={test_cooperative.id}",
        json={"period_start": "2026-09-01", "period_end": "2026-09-30"},
    ).json()
    payout_id = approved[0]["id"]
    seen_refs = []

    async def fake_transfer(*, receiver_phone, amount, reference, external_ref=None, **kwargs):
        seen_refs.append(external_ref)
        return {
            "success": True,
            "moolre_transfer_ref": external_ref,
            "external_ref": external_ref,
            "message": "ok",
            "raw": {},
        }

    async def fake_sms(*args, **kwargs):
        return {"success": True}

    monkeypatch.setattr(
        "app.services.moolre_service.MoolreService.initiate_transfer",
        fake_transfer,
    )
    monkeypatch.setattr(
        "app.services.communications_service.CommunicationsService.send_single_sms",
        fake_sms,
    )

    res = auth_client.post(
        f"/payroll/disburse?cooperative_id={test_cooperative.id}",
        json={"period_start": "2026-09-01", "period_end": "2026-09-30"},
    )
    assert res.status_code == 200
    payouts = res.json()
    assert payouts[0]["status"] == "paid"
    assert seen_refs == [f"wage-payout-{payout_id}"]
    assert payouts[0]["moolre_reference"] == f"wage-payout-{payout_id}"
