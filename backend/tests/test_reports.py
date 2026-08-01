"""Focused tests for cooperative-scoped CSV reports."""

import csv
import io
from datetime import datetime

from app.models.models import AdminAuditLog, CooperativeMembership, Production


def _rows(response):
    return list(csv.reader(io.StringIO(response.text)))


def test_members_export_is_scoped_and_audited(client, db, farmer, cooperative):
    other = client.post("/cooperatives/", json={"name": "Other Cooperative", "currency": "GHS"}).json()
    client.post(
        "/farmers/",
        json={
            "name": "Other Member",
            "phone": "+233551009999",
            "cooperative_id": other["id"],
        },
    )

    response = client.get(f"/reports/members.csv?cooperative_id={cooperative['id']}&q=Kofi")

    assert response.status_code == 200
    rows = _rows(response)
    assert rows[0][0:3] == ["Member ID", "Name", "Phone"]
    assert len(rows) == 2
    assert rows[1][1] == farmer["name"]
    assert "Other Member" not in response.text
    audit = db.query(AdminAuditLog).order_by(AdminAuditLog.id.desc()).first()
    assert audit.action == "report.export"
    assert audit.resource_id == "members"
    assert audit.cooperative_id == cooperative["id"]
    assert '"row_count": 1' in audit.details
    assert "Kofi" not in audit.details
    assert '"search_applied": true' in audit.details


def test_unified_member_and_score_exports_include_production_focus(
    client, db, farmer, cooperative
):
    membership = db.query(CooperativeMembership).filter_by(id=farmer["id"]).one()
    membership.production_focus = "mixed"
    membership.animal_type = "Goats"
    membership.animal_scale = 12
    db.flush()

    members = _rows(
        client.get(f"/reports/members.csv?cooperative_id={cooperative['id']}")
    )
    scores = _rows(
        client.get(f"/reports/scores.csv?cooperative_id={cooperative['id']}")
    )

    assert members[0][5:10] == [
        "Production Focus",
        "Animal Type",
        "Animal Scale",
        "Crop",
        "Acreage",
    ]
    assert members[1][5:8] == ["mixed", "Goats", "12"]
    assert scores[0][2:6] == [
        "Production Focus",
        "Animal Type",
        "Animal Scale",
        "Crop",
    ]
    assert scores[1][2:5] == ["mixed", "Goats", "12"]


def test_production_export_includes_unified_and_legacy_columns(
    client, db, farmer, cooperative
):
    record = Production(
        farmer_id=farmer["id"],
        production_kind="animal",
        product_name="Eggs",
        activity="collection",
        expected_quantity=80,
        quantity=76,
        unit="crates",
        production_date=datetime.utcnow(),
    )
    legacy = Production(
        farmer_id=farmer["id"],
        crop_type="Poultry",
        expected_kg=80,
        quantity_kg=76,
        harvest_date=datetime.utcnow(),
    )
    db.add_all([record, legacy])
    db.flush()

    animal_response = client.get(
        f"/reports/production.csv?cooperative_id={cooperative['id']}"
        "&status=completed&q=Eggs"
    )
    legacy_response = client.get(
        f"/reports/production.csv?cooperative_id={cooperative['id']}"
        "&status=completed&q=Poultry"
    )

    assert animal_response.status_code == 200
    animal_rows = _rows(animal_response)
    assert animal_rows[0][2:9] == [
        "Production Kind",
        "Product",
        "Activity",
        "Expected Quantity",
        "Actual Quantity",
        "Unit",
        "Production Date",
    ]
    assert animal_rows[1][2:8] == ["animal", "Eggs", "collection", "80", "76", "crates"]

    assert legacy_response.status_code == 200
    legacy_rows = _rows(legacy_response)
    assert legacy_rows[1][9:12] == ["Poultry", "80", "76"]


def test_payment_export_filters_status_and_date(client, transaction, cooperative):
    response = client.get(
        f"/reports/payments.csv?cooperative_id={cooperative['id']}"
        "&status=pending&start_date=2000-01-01&end_date=2100-01-01"
    )

    assert response.status_code == 200
    rows = _rows(response)
    assert len(rows) == 2
    assert rows[1][0] == str(transaction["id"])
    assert rows[1][7] == "pending"


def test_loan_export_includes_operational_status(client, farmer, cooperative):
    loan = client.post(
        "/loans/",
        json={"farmer_id": farmer["id"], "amount": 300, "purpose": "Seed"},
    ).json()

    response = client.get(
        f"/reports/loans.csv?cooperative_id={cooperative['id']}&status=requested"
    )

    assert response.status_code == 200
    rows = _rows(response)
    assert rows[0][0:3] == ["Loan ID", "Member", "Amount"]
    assert rows[1][0] == str(loan["id"])
    assert rows[1][5] == "requested"


def test_reports_reject_reversed_date_range(client, cooperative):
    response = client.get(
        f"/reports/scores.csv?cooperative_id={cooperative['id']}"
        "&start_date=2026-08-01&end_date=2026-07-01"
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "start_date must be on or before end_date"
