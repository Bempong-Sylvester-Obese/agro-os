"""Daily idempotent loan repayment reminder job for Render Cron."""

import asyncio
import logging
from datetime import date

from app.database.db import create_session
from app.models.models import CooperativeMembership as Farmer
from app.models.models import Loan, LoanStatus
from app.services.communications_service import CommunicationsService

logger = logging.getLogger(__name__)


def reminder_kind(due_date: date, today: date) -> str | None:
    days_until = (due_date - today).days
    if days_until in (7, 3, 1):
        return f"due_in_{days_until}_days"
    if days_until == 0:
        return "due_today"
    days_overdue = -days_until
    if days_overdue in (1, 3, 7) or (days_overdue > 7 and days_overdue % 7 == 0):
        return f"overdue_{days_overdue}_days"
    return None


async def run(today: date | None = None) -> dict[str, int]:
    target_date = today or date.today()
    db = create_session()
    sent = failed = skipped = 0
    try:
        loans = (
            db.query(Loan)
            .filter(
                Loan.status == LoanStatus.disbursed,
                Loan.expected_repayment_date.is_not(None),
            )
            .all()
        )
        service = CommunicationsService()
        for loan in loans:
            kind = reminder_kind(loan.expected_repayment_date, target_date)
            if not kind:
                skipped += 1
                continue
            farmer = db.query(Farmer).filter(Farmer.id == loan.farmer_id).first()
            if not farmer:
                failed += 1
                continue
            try:
                reminder = await service.send_loan_repayment_reminder(
                    loan=loan,
                    farmer=farmer,
                    reminder_kind=kind,
                    scheduled_for=target_date,
                    db=db,
                )
                if reminder.status == "sent":
                    sent += 1
                else:
                    failed += 1
            except Exception:
                db.rollback()
                failed += 1
                logger.exception("Loan reminder failed for loan %s", loan.id)
        return {"sent": sent, "failed": failed, "skipped": skipped}
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = asyncio.run(run())
    logger.info("Loan reminder job complete: %s", result)
