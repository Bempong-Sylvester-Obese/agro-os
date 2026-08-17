import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.models import Cooperative, User
from app.models.wage_payout import PayoutStatus, WagePayout
from app.models.worker import Worker
from app.models.worker_attendance import WorkerAttendance
from app.schemas.wage_payout import (
    PayrollHistoryResponse,
    PayrollPeriod,
    PayrollSummaryItem,
    PayrollSummaryResponse,
    WagePayoutResponse,
)
from app.services.auth_service import (
    enforce_cooperative_scope,
    get_current_user,
    require_roles,
)
from app.services.communications_service import CommunicationsService

router = APIRouter(prefix="/payroll", tags=["payroll"])
logger = logging.getLogger(__name__)


@router.get("/summary", response_model=PayrollSummaryResponse)
def payroll_summary(
    cooperative_id: int = Query(...),
    period_start: date = Query(...),
    period_end: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    coop = db.query(Cooperative).filter(Cooperative.id == cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")

    rows = (
        db.query(
            WorkerAttendance.worker_id,
            Worker.name,
            Worker.phone,
            Worker.wage_rate,
            func.coalesce(func.sum(WorkerAttendance.hours_worked), 0).label("total_hours"),
            func.count(WorkerAttendance.id).label("total_shifts"),
        )
        .join(
            Worker,
            (WorkerAttendance.worker_id == Worker.id)
            & (WorkerAttendance.cooperative_id == Worker.cooperative_id),
        )
        .filter(
            WorkerAttendance.cooperative_id == cooperative_id,
            WorkerAttendance.date >= period_start,
            WorkerAttendance.date <= period_end,
        )
        .group_by(WorkerAttendance.worker_id, Worker.name, Worker.phone, Worker.wage_rate)
        .all()
    )

    items = []
    total_gross = 0.0
    for r in rows:
        gross = float(r.total_hours) * float(r.wage_rate)
        items.append(
            PayrollSummaryItem(
                worker_id=r.worker_id,
                worker_name=r.name,
                phone=r.phone,
                wage_rate=float(r.wage_rate),
                total_hours=float(r.total_hours),
                total_shifts=r.total_shifts,
                gross_amount=round(gross, 2),
            )
        )
        total_gross += gross

    return PayrollSummaryResponse(
        period_start=period_start,
        period_end=period_end,
        total_workers=len(items),
        total_gross=round(total_gross, 2),
        items=items,
    )


@router.post("/approve", response_model=list[WagePayoutResponse], status_code=201)
def approve_payroll(
    data: PayrollPeriod,
    cooperative_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "farm_owner", "farm_manager")),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    coop = db.query(Cooperative).filter(Cooperative.id == cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")

    existing = (
        db.query(WagePayout)
        .filter(
            WagePayout.cooperative_id == cooperative_id,
            WagePayout.period_start == data.period_start,
            WagePayout.period_end == data.period_end,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Payroll already approved for this period")

    rows = (
        db.query(
            WorkerAttendance.worker_id,
            Worker.name,
            Worker.phone,
            Worker.wage_rate,
            func.coalesce(func.sum(WorkerAttendance.hours_worked), 0).label("total_hours"),
            func.count(WorkerAttendance.id).label("total_shifts"),
        )
        .join(
            Worker,
            (WorkerAttendance.worker_id == Worker.id)
            & (WorkerAttendance.cooperative_id == Worker.cooperative_id),
        )
        .filter(
            WorkerAttendance.cooperative_id == cooperative_id,
            WorkerAttendance.date >= data.period_start,
            WorkerAttendance.date <= data.period_end,
        )
        .group_by(WorkerAttendance.worker_id, Worker.name, Worker.phone, Worker.wage_rate)
        .all()
    )

    payouts = []
    for r in rows:
        gross = round(float(r.total_hours) * float(r.wage_rate), 2)
        payout = WagePayout(
            cooperative_id=cooperative_id,
            worker_id=r.worker_id,
            period_start=data.period_start,
            period_end=data.period_end,
            total_hours=float(r.total_hours),
            total_shifts=r.total_shifts,
            wage_rate=float(r.wage_rate),
            gross_amount=gross,
            status=PayoutStatus.approved,
            approved_by=current_user.id if current_user else None,
            approved_at=datetime.utcnow(),
        )
        db.add(payout)
        payouts.append(payout)

    db.commit()
    for p in payouts:
        db.refresh(p)
    return payouts


@router.post("/disburse", response_model=list[WagePayoutResponse])
async def disburse_payroll(
    data: PayrollPeriod,
    cooperative_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "farm_owner")),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    coop = db.query(Cooperative).filter(Cooperative.id == cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")

    payout_ids = [
        payout_id
        for (payout_id,) in (
            db.query(WagePayout.id)
            .filter(
                WagePayout.cooperative_id == cooperative_id,
                WagePayout.period_start == data.period_start,
                WagePayout.period_end == data.period_end,
                WagePayout.status == PayoutStatus.approved,
            )
            .all()
        )
    ]

    if not payout_ids:
        raise HTTPException(status_code=404, detail="No approved payouts found for this period")

    from app.services.providers.factory import get_payment_provider

    moolre = get_payment_provider()
    results = []
    paid_notifications: list[tuple[float, date, date, str]] = []

    for payout_id in payout_ids:
        payout = (
            db.query(WagePayout)
            .filter(
                WagePayout.id == payout_id,
                WagePayout.cooperative_id == cooperative_id,
                WagePayout.status == PayoutStatus.approved,
            )
            .with_for_update()
            .first()
        )
        if not payout:
            # Another request already moved this payout out of approved.
            finalized = db.query(WagePayout).filter(WagePayout.id == payout_id).first()
            if finalized:
                results.append(finalized)
            continue

        worker = (
            db.query(Worker)
            .filter(
                Worker.id == payout.worker_id,
                Worker.cooperative_id == cooperative_id,
            )
            .first()
        )
        if not worker:
            payout.status = PayoutStatus.failed
            payout.failure_reason = "Worker not found"
            db.commit()
            db.refresh(payout)
            results.append(payout)
            continue

        external_ref = payout.moolre_reference or f"wage-payout-{payout.id}"
        payout.moolre_reference = external_ref
        amount = payout.gross_amount
        period_start = payout.period_start
        period_end = payout.period_end
        worker_phone = worker.phone
        db.commit()

        try:
            transfer = await moolre.initiate_transfer(
                receiver_phone=worker_phone,
                amount=amount,
                reference=f"Wage payout #{payout_id}",
                external_ref=external_ref,
            )
            payout = (
                db.query(WagePayout)
                .filter(WagePayout.id == payout_id)
                .with_for_update()
                .one()
            )
            if transfer.get("success"):
                payout.status = PayoutStatus.paid
                payout.paid_at = datetime.utcnow()
                payout.moolre_reference = (
                    transfer.get("moolre_transfer_ref")
                    or transfer.get("external_ref")
                    or external_ref
                )
                payout.failure_reason = None
                if worker_phone:
                    paid_notifications.append(
                        (amount, period_start, period_end, worker_phone)
                    )
            else:
                payout.status = PayoutStatus.failed
                payout.failure_reason = transfer.get("message", "Moolre transfer failed")
        except Exception as e:
            logger.exception("Moolre transfer failed for payout %s", payout_id)
            payout = (
                db.query(WagePayout)
                .filter(WagePayout.id == payout_id)
                .with_for_update()
                .one()
            )
            payout.status = PayoutStatus.failed
            payout.failure_reason = str(e)

        db.commit()
        db.refresh(payout)
        results.append(payout)

    if paid_notifications:
        comm = CommunicationsService()
        for amount, period_start, period_end, phone in paid_notifications:
            await comm.send_single_sms(
                recipient=phone,
                message=(
                    f"Payment of GHS {amount:.2f} for "
                    f"{period_start} to {period_end} has been sent "
                    f"to your mobile money wallet."
                ),
                db=db,
                cooperative_id=cooperative_id,
            )

    return results


@router.get("/history", response_model=list[PayrollHistoryResponse])
def payroll_history(
    cooperative_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    enforce_cooperative_scope(current_user, cooperative_id)
    coop = db.query(Cooperative).filter(Cooperative.id == cooperative_id).first()
    if not coop:
        raise HTTPException(status_code=404, detail="Cooperative not found")

    periods = (
        db.query(
            WagePayout.period_start,
            WagePayout.period_end,
            WagePayout.status,
            func.count(WagePayout.id).label("total_workers"),
            func.sum(WagePayout.gross_amount).label("total_gross"),
            func.max(WagePayout.paid_at).label("paid_at"),
        )
        .filter(WagePayout.cooperative_id == cooperative_id)
        .group_by(WagePayout.period_start, WagePayout.period_end, WagePayout.status)
        .order_by(WagePayout.period_start.desc())
        .all()
    )

    result = []
    for period in periods:
        payouts = (
            db.query(WagePayout)
            .filter(
                WagePayout.cooperative_id == cooperative_id,
                WagePayout.period_start == period.period_start,
                WagePayout.period_end == period.period_end,
                WagePayout.status == period.status,
            )
            .all()
        )
        result.append(
            PayrollHistoryResponse(
                period_start=period.period_start,
                period_end=period.period_end,
                status=period.status,
                total_workers=period.total_workers,
                total_gross=float(period.total_gross or 0),
                paid_at=period.paid_at,
                payouts=[WagePayoutResponse.model_validate(p) for p in payouts],
            )
        )

    return result
