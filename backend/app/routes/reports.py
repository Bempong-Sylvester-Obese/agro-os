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
    AggregationBatch,
    Buyer,
    CooperativeMembership,
    Farmer,
    Loan,
    LoanStatus,
    MembershipStatus,
    ProduceIntake,
    ProduceSale,
    Production,
    ReceiptStatus,
    SettlementLine,
    SettlementLineStatus,
    SettlementRun,
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
    value = getattr(value, "value", value)
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = "" if value is None else str(value)
    return f"'{text}" if text.startswith(("=", "+", "-", "@")) else text


def _production_value(record: Production, generic_name: str, legacy_name: str):
    value = getattr(record, generic_name, None)
    return value if value is not None else getattr(record, legacy_name, None)


def _production_date(record: Production):
    return _production_value(record, "production_date", "harvest_date")


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
        [
            m.id,
            m.name,
            m.phone,
            m.email,
            m.location,
            getattr(m, "production_focus", None),
            getattr(m, "animal_type", None),
            getattr(m, "animal_scale", None),
            m.crop_type,
            m.acreage,
            m.membership_status.value,
            m.trust_score,
            m.created_at,
        ]
        for m in members
    ]
    return _csv_response(
        report="members",
        headers=[
            "Member ID",
            "Name",
            "Phone",
            "Email",
            "Location",
            "Production Focus",
            "Animal Type",
            "Animal Scale",
            "Crop",
            "Acreage",
            "Status",
            "Trust Score",
            "Joined",
        ],
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
    status: str | None = Query(default=None, pattern="^(planned|completed|harvested)$"),
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
        search_columns = [Farmer.name, Production.crop_type]
        for name in ("product_name", "activity"):
            column = getattr(Production, name, None)
            if column is not None:
                search_columns.append(column)
        query = query.filter(or_(*(column.ilike(term) for column in search_columns)))
    completion_column = getattr(Production, "production_date", Production.harvest_date)
    if status in {"completed", "harvested"}:
        query = query.filter(completion_column.is_not(None))
    elif status == "planned":
        query = query.filter(completion_column.is_(None))
    records = query.order_by(Production.created_at.desc()).all()
    rows = [
        [
            record.id,
            record.farmer.name,
            getattr(record, "production_kind", None),
            getattr(record, "product_name", None),
            getattr(record, "activity", None),
            _production_value(record, "expected_quantity", "expected_kg"),
            _production_value(record, "quantity", "quantity_kg"),
            getattr(record, "unit", None) or "kg",
            _production_date(record),
            record.crop_type,
            record.expected_kg,
            record.quantity_kg,
            record.harvest_date,
            record.season,
            record.quality_grade,
            record.created_at,
        ]
        for record in records
    ]
    return _csv_response(
        report="production",
        headers=[
            "Production ID",
            "Member",
            "Production Kind",
            "Product",
            "Activity",
            "Expected Quantity",
            "Actual Quantity",
            "Unit",
            "Production Date",
            "Crop",
            "Expected (kg)",
            "Harvest (kg)",
            "Harvest Date",
            "Season",
            "Quality Grade",
            "Logged Date",
        ],
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
            getattr(member, "production_focus", None),
            getattr(member, "animal_type", None),
            getattr(member, "animal_scale", None),
            member.crop_type,
            member.trust_score,
            "eligible" if member.trust_score >= 68 else "review",
            latest.get(member.id).calculated_at if latest.get(member.id) else None,
        ]
        for member in members
    ]
    return _csv_response(
        report="scores",
        headers=[
            "Member ID",
            "Member",
            "Production Focus",
            "Animal Type",
            "Animal Scale",
            "Crop",
            "Trust Score",
            "Decision",
            "Calculated At",
        ],
        rows=rows,
        cooperative_id=scope,
        current_user=current_user,
        db=db,
        filters=_audit_filters(q, status, start_date, end_date),
    )


@router.get("/intake.csv")
def export_intake(
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    scope = _scope(current_user, cooperative_id)
    records = (
        db.query(ProduceIntake)
        .options(joinedload(ProduceIntake.membership).joinedload(CooperativeMembership.farmer))
        .filter(ProduceIntake.cooperative_id == scope)
        .order_by(ProduceIntake.received_at.desc())
        .all()
    )
    return _csv_response(
        report="intake",
        headers=[
            "Intake ID",
            "Member",
            "Crop",
            "Gross kg",
            "Net kg",
            "Grade",
            "Collection Point",
            "Status",
            "Received",
        ],
        rows=[
            [
                record.id,
                record.membership.name,
                record.crop_type,
                record.quantity_kg,
                record.net_quantity_kg,
                record.quality_grade,
                record.collection_point,
                record.status.value,
                record.received_at,
            ]
            for record in records
        ],
        cooperative_id=scope,
        current_user=current_user,
        db=db,
        filters={},
    )


@router.get("/aggregation.csv")
def export_aggregation(
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    scope = _scope(current_user, cooperative_id)
    records = (
        db.query(AggregationBatch)
        .filter(AggregationBatch.cooperative_id == scope)
        .order_by(AggregationBatch.created_at.desc())
        .all()
    )
    return _csv_response(
        report="aggregation",
        headers=["Batch ID", "Code", "Crop", "Quantity kg", "Status", "Closed"],
        rows=[
            [
                record.id,
                record.code,
                record.crop_type,
                record.total_quantity_kg,
                record.status.value,
                record.closed_at,
            ]
            for record in records
        ],
        cooperative_id=scope,
        current_user=current_user,
        db=db,
        filters={},
    )


@router.get("/sales.csv")
def export_sales(
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    scope = _scope(current_user, cooperative_id)
    records = (
        db.query(ProduceSale)
        .options(
            joinedload(ProduceSale.buyer),
            joinedload(ProduceSale.aggregation_batch),
            joinedload(ProduceSale.receipts),
        )
        .filter(ProduceSale.cooperative_id == scope)
        .order_by(ProduceSale.created_at.desc())
        .all()
    )
    return _csv_response(
        report="sales",
        headers=[
            "Sale ID",
            "Buyer",
            "Batch",
            "Quantity kg",
            "Unit Price",
            "Gross",
            "Verified Funds",
            "Outstanding",
            "Status",
            "Sold",
        ],
        rows=[
            [
                record.id,
                record.buyer.name,
                record.aggregation_batch.code,
                record.quantity_kg,
                record.unit_price,
                record.gross_amount,
                sum(
                    (
                        receipt.amount
                        for receipt in record.receipts
                        if receipt.status == ReceiptStatus.verified
                    ),
                    0,
                ),
                record.gross_amount
                - sum(
                    (
                        receipt.amount
                        for receipt in record.receipts
                        if receipt.status == ReceiptStatus.verified
                    ),
                    0,
                ),
                record.status.value,
                record.sold_at,
            ]
            for record in records
        ],
        cooperative_id=scope,
        current_user=current_user,
        db=db,
        filters={},
    )


@router.get("/buyers.csv")
def export_buyers(
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    scope = _scope(current_user, cooperative_id)
    records = (
        db.query(Buyer)
        .filter(Buyer.cooperative_id == scope)
        .order_by(Buyer.name)
        .all()
    )
    return _csv_response(
        report="buyers",
        headers=["Buyer ID", "Name", "Phone", "Email", "Address", "Active"],
        rows=[
            [
                record.id,
                record.name,
                record.phone,
                record.email,
                record.address,
                record.is_active,
            ]
            for record in records
        ],
        cooperative_id=scope,
        current_user=current_user,
        db=db,
        filters={},
    )


@router.get("/settlements.csv")
def export_settlements(
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    scope = _scope(current_user, cooperative_id)
    records = (
        db.query(SettlementRun)
        .filter(SettlementRun.cooperative_id == scope)
        .order_by(SettlementRun.created_at.desc())
        .all()
    )
    return _csv_response(
        report="settlements",
        headers=[
            "Settlement ID",
            "Sale ID",
            "Gross",
            "Deductions",
            "Net",
            "Status",
            "Approved",
            "Completed",
        ],
        rows=[
            [
                record.id,
                record.sale_id,
                record.gross_total,
                record.deductions_total,
                record.net_total,
                record.status.value,
                record.approved_at,
                record.completed_at,
            ]
            for record in records
        ],
        cooperative_id=scope,
        current_user=current_user,
        db=db,
        filters={},
    )


@router.get("/payout-exceptions.csv")
def export_payout_exceptions(
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    scope = _scope(current_user, cooperative_id)
    records = (
        db.query(SettlementLine)
        .options(
            joinedload(SettlementLine.membership).joinedload(
                CooperativeMembership.farmer
            ),
            joinedload(SettlementLine.settlement_run),
        )
        .join(SettlementRun)
        .filter(
            SettlementRun.cooperative_id == scope,
            SettlementLine.status == SettlementLineStatus.failed,
        )
        .order_by(SettlementLine.updated_at.desc())
        .all()
    )
    return _csv_response(
        report="payout-exceptions",
        headers=[
            "Settlement ID",
            "Line ID",
            "Member",
            "Net Amount",
            "Reference",
            "Error",
        ],
        rows=[
            [
                record.settlement_run_id,
                record.id,
                record.membership.name,
                record.net_amount,
                record.payout_reference,
                record.last_error,
            ]
            for record in records
        ],
        cooperative_id=scope,
        current_user=current_user,
        db=db,
        filters={},
    )
