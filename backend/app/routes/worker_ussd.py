from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.worker import Worker
from app.models.work_task import TaskStatus, WorkTask
from app.models.wage_payout import PayoutStatus, WagePayout
from app.schemas.ussd_schemas import UssdRequest, UssdResponse

router = APIRouter(prefix="/ussd/worker", tags=["worker-ussd"])


def resolve_worker(phone: str, db: Session) -> Worker | None:
    return db.query(Worker).filter(Worker.phone == phone, Worker.status == "active").first()


@router.post("/menu", response_model=UssdResponse)
def worker_menu(req: UssdRequest, db: Session = Depends(get_db)):
    worker = resolve_worker(req.phone, db)
    if not worker:
        return UssdResponse(response="END Worker not found. Contact your farm manager.", session_id=req.session_id)

    text = req.text.strip()
    parts = text.split("*") if text else []
    step = len(parts)

    if step == 0:
        return UssdResponse(
            response="CON Welcome to AgroOS Worker Portal\n1. My Schedule\n2. My Pay\n0. Exit",
            session_id=req.session_id,
        )
    elif step == 1:
        choice = parts[0]
        if choice == "1":
            today = date.today()
            tasks = (
                db.query(WorkTask)
                .filter(
                    WorkTask.cooperative_id == worker.cooperative_id,
                    WorkTask.scheduled_date >= today,
                    WorkTask.status.in_([TaskStatus.open, TaskStatus.in_progress]),
                )
                .order_by(WorkTask.scheduled_date)
                .limit(5)
                .all()
            )
            if not tasks:
                return UssdResponse(response="END No upcoming tasks.", session_id=req.session_id)
            lines = [f"{t.scheduled_date} - {t.title} ({t.task_type.value})" for t in tasks]
            return UssdResponse(response="END " + "\n".join(lines), session_id=req.session_id)
        elif choice == "2":
            payouts = (
                db.query(WagePayout)
                .filter(
                    WagePayout.worker_id == worker.id,
                    WagePayout.status.in_([PayoutStatus.approved, PayoutStatus.paid]),
                )
                .order_by(WagePayout.created_at.desc())
                .limit(3)
                .all()
            )
            if not payouts:
                return UssdResponse(response="END No pay history.", session_id=req.session_id)
            lines = []
            for p in payouts:
                status_icon = "✅" if p.status == PayoutStatus.paid else "⏳"
                lines.append(f"{status_icon} GHS {p.gross_amount:.2f} ({p.period_start} to {p.period_end})")
            return UssdResponse(response="END " + "\n".join(lines), session_id=req.session_id)
        else:
            return UssdResponse(response="END Goodbye.", session_id=req.session_id)

    return UssdResponse(response="END Invalid option.", session_id=req.session_id)
