"""Cooperative-scoped CSV exports for administrator dashboards."""

import csv
import io
import json
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.database.db import get_db
from app.dependencies.cooperative_scope import resolve_cooperative_scope
from app.models.models import (
    AdminAuditLog,
    CooperativeMembership,
    Farmer,
    Loan,
    LoanStatus,
    MembershipStatus,
    Production,
    Transaction,
    TransactionStatus,
    TrustScore,
    User,
)
from app.services.auth_service import require_roles

router = APIRouter(prefix="/reports", tags=["reports"])


def _scope(current_user: User | None, cooperative_id: int | None) -> int:
    return resolve_cooperative_scope(
        current_user=current_user,
        cooperative_id=cooperative_id,
        settings=get_settings(),
    )


def _date_bounds(start_date: date | None, end_date: date | None):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be on or before end_date")
    start = datetime.combine(start_date, time.min) if start_date else None
    end = datetime.combine(end_date + timedelta(days=1), time.min) if end_date else None
    return start, end


def _apply_dates(query, column, start_date: date | None, end_date: date | None):
    start, end = _date_bounds(start_date, end_date)
    if start:
        query = query.filter(column >= start)
    if end:
        query = query.filter(column < end)
    return query


def _safe_cell(value) -> str:
    text = "" if value is None else str(value)
    return f"'{text}" if text.startswith(("=", "+", "-", "@")) else text


def _audit_filters(q, status, start_date, end_date) -> dict:
    """Return useful export metadata without persisting search terms."""
    return {
        "search_applied": bool(q and q.strip()),
        "status": status.value if hasattr(status, "value") else status,
        "start_date": start_date,
        "end_date": end_date,
    }


def _csv_response(
    *,
    report: str,
    headers: list[str],
    rows: list[list],
    cooperative_id: int,
    current_user: User | None,
    db: Session,
    filters: dict,
):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows([[_safe_cell(value) for value in row] for row in rows])

    db.add(
        AdminAuditLog(
            cooperative_id=cooperative_id,
            actor_id=str(current_user.id) if current_user else "system:local-development",
            action="report.export",
            resource_type="report",
            resource_id=report,
            details=json.dumps({"row_count": len(rows), "filters": filters}, default=str),
        )
    )
    db.commit()

    filename = f"{report}-{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _base_members_query(db: Session, cooperative_id: int):
    return (
        db.query(CooperativeMembership)
        .options(joinedload(CooperativeMembership.farmer))
        .join(Farmer)
        .filter(CooperativeMembership.cooperative_id == cooperative_id)
    )


@router.get("/members.csv")
def export_members(
    cooperative_id: int | None = None,
    q: str | None = None,
    status: MembershipStatus | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    scope = _scope(current_user, cooperative_id)
    query = _apply_dates(_base_members_query(db, scope), CooperativeMembership.created_at, start_date, end_date)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(or_(Farmer.name.ilike(term), Farmer.phone.ilike(term)))
    if status:
        query = query.filter(CooperativeMembership.membership_status == status)
    members = query.order_by(Farmer.name).all()
    rows = [
        [m.id, m.name, m.phone, m.email, m.location, m.crop_type, m.acreage, m.membership_status.value, m.trust_score, m.created_at]
        for m in members
    ]
    return _csv_response(
        report="members",
        headers=["Member ID", "Name", "Phone", "Email", "Location", "Crop", "Acreage", "Status", "Trust Score", "Joined"],
        rows=rows,
        cooperative_id=scope,
        current_user=current_user,
        db=db,
        filters=_audit_filters(q, status, start_date, end_date),
    )


@router.get("/payments.csv")
def export_payments(
    cooperative_id: int | None = None,
    q: str | None = None,
    status: TransactionStatus | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    scope = _scope(current_user, cooperative_id)
    query = (
        db.query(Transaction)
        .options(
            joinedload(Transaction.farmer).joinedload(CooperativeMembership.farmer)
        )
        .join(CooperativeMembership, Transaction.farmer_id == CooperativeMembership.id)
        .join(Farmer)
        .filter(CooperativeMembership.cooperative_id == scope)
    )
    query = _apply_dates(query, Transaction.created_at, start_date, end_date)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(or_(Farmer.name.ilike(term), Farmer.phone.ilike(term)))
    if status:
        query = query.filter(Transaction.status == status)
    records = query.order_by(Transaction.created_at.desc()).all()
    rows = [
        [tx.id, tx.farmer.name, tx.farmer.phone, tx.transaction_type.value, tx.amount, tx.currency, tx.channel, tx.status.value, tx.created_at]
        for tx in records
    ]
    return _csv_response(
        report="payments",
        headers=["Transaction ID", "Member", "Phone", "Type", "Amount", "Currency", "Channel", "Status", "Date"],
        rows=rows,
        cooperative_id=scope,
        current_user=current_user,
        db=db,
        filters=_audit_filters(q, status, start_date, end_date),
    )


@router.get("/loans.csv")
def export_loans(
    cooperative_id: int | None = None,
    q: str | None = None,
    status: LoanStatus | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    scope = _scope(current_user, cooperative_id)
    query = (
        db.query(Loan)
        .options(joinedload(Loan.farmer).joinedload(CooperativeMembership.farmer))
        .join(CooperativeMembership, Loan.farmer_id == CooperativeMembership.id)
        .join(Farmer)
        .filter(CooperativeMembership.cooperative_id == scope)
    )
    query = _apply_dates(query, Loan.created_at, start_date, end_date)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(or_(Farmer.name.ilike(term), Farmer.phone.ilike(term)))
    if status:
        query = query.filter(Loan.status == status)
    records = query.order_by(Loan.created_at.desc()).all()
    rows = [
        [
            loan.id,
            loan.farmer.name,
            loan.amount,
            loan.currency,
            loan.purpose,
            loan.status.value,
            loan.moolre_transfer_ref,
            loan.expected_repayment_date,
            loan.created_at,
        ]
        for loan in records
    ]
    return _csv_response(
        report="loans",
        headers=[
            "Loan ID",
            "Member",
            "Amount",
            "Currency",
            "Purpose",
            "Status",
            "Transfer Reference",
            "Expected Repayment",
            "Created",
        ],
        rows=rows,
        cooperative_id=scope,
        current_user=current_user,
        db=db,
        filters=_audit_filters(q, status, start_date, end_date),
    )


@router.get("/production.csv")
def export_production(
    cooperative_id: int | None = None,
    q: str | None = None,
    status: str | None = Query(default=None, pattern="^(planned|harvested)$"),
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    scope = _scope(current_user, cooperative_id)
    query = (
        db.query(Production)
        .options(
            joinedload(Production.farmer).joinedload(CooperativeMembership.farmer)
        )
        .join(CooperativeMembership, Production.farmer_id == CooperativeMembership.id)
        .join(Farmer)
        .filter(CooperativeMembership.cooperative_id == scope)
    )
    query = _apply_dates(query, Production.created_at, start_date, end_date)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(or_(Farmer.name.ilike(term), Production.crop_type.ilike(term)))
    if status == "harvested":
        query = query.filter(Production.harvest_date.is_not(None))
    elif status == "planned":
        query = query.filter(Production.harvest_date.is_(None))
    records = query.order_by(Production.created_at.desc()).all()
    rows = [
        [record.id, record.farmer.name, record.crop_type, record.expected_kg, record.quantity_kg, record.harvest_date, record.created_at]
        for record in records
    ]
    return _csv_response(
        report="production",
        headers=["Production ID", "Member", "Crop", "Expected (kg)", "Harvest (kg)", "Harvest Date", "Logged Date"],
        rows=rows,
        cooperative_id=scope,
        current_user=current_user,
        db=db,
        filters=_audit_filters(q, status, start_date, end_date),
    )


@router.get("/scores.csv")
def export_scores(
    cooperative_id: int | None = None,
    q: str | None = None,
    status: str | None = Query(default=None, pattern="^(eligible|review)$"),
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    scope = _scope(current_user, cooperative_id)
    query = _apply_dates(_base_members_query(db, scope), CooperativeMembership.updated_at, start_date, end_date)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(or_(Farmer.name.ilike(term), Farmer.phone.ilike(term)))
    if status == "eligible":
        query = query.filter(CooperativeMembership.trust_score >= 68)
    elif status == "review":
        query = query.filter(CooperativeMembership.trust_score < 68)
    members = query.order_by(CooperativeMembership.trust_score.desc()).all()
    latest = {}
    if members:
        snapshots = (
            db.query(TrustScore)
            .filter(TrustScore.farmer_id.in_([member.id for member in members]))
            .order_by(TrustScore.farmer_id, TrustScore.calculated_at.desc())
            .all()
        )
        for snapshot in snapshots:
            latest.setdefault(snapshot.farmer_id, snapshot)
    rows = [
        [
            member.id,
            member.name,
            member.crop_type,
            member.trust_score,
            "eligible" if member.trust_score >= 68 else "review",
            latest.get(member.id).calculated_at if latest.get(member.id) else None,
        ]
        for member in members
    ]
    return _csv_response(
        report="scores",
        headers=["Member ID", "Member", "Crop", "Trust Score", "Decision", "Calculated At"],
        rows=rows,
        cooperative_id=scope,
        current_user=current_user,
        db=db,
        filters=_audit_filters(q, status, start_date, end_date),
    )
