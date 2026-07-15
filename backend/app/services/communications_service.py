"""
Communications Service

Wraps Moolre SMS sending with AgroOS-specific templates and
persists all outbound messages to CommunicationLog.
"""

import uuid
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models.models import (
    CommunicationLog,
    Loan,
    LoanReminder,
    MessageType,
)
from app.models.models import (
    CooperativeMembership as Farmer,
)
from app.services.moolre_service import MoolreService


class CommunicationsService:
    """Send SMS messages and log all communication."""

    def __init__(self) -> None:
        self.moolre = MoolreService()

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def send_dues_reminder(
        self,
        farmer: Farmer,
        amount: float,
        due_date: str,
        db: Session,
        sent_by: str | None = None,
    ) -> dict:
        """Send a dues reminder with the configured AgroOS menu code."""
        from app.config import get_settings

        settings = get_settings()
        ussd_code = settings.agroos_ussd_code.strip() or "*919*4020#"

        message = (
            f"Dear {farmer.name}, your cooperative dues of GHS {amount:.2f} are due by {due_date}. "
            f"Dial {ussd_code} and choose Pay Dues. - AgroOS"
        )

        result = await self.moolre.send_single_sms(
            phone=farmer.phone,
            message=message,
            ref=str(uuid.uuid4()),
        )

        log = self._log(
            db=db,
            message_type=MessageType.sms,
            cooperative_id=farmer.cooperative_id,
            recipients_count=1,
            body=message,
            moolre_ref=result.get("raw", {}).get("data"),
            sent_by=sent_by,
            status="sent" if result["success"] else "failed",
        )

        return {
            "success": result["success"],
            "message": result["message"],
            "log_id": log.id,
        }

    async def send_payment_confirmation(
        self,
        farmer: Farmer,
        amount: float,
        reference: str,
        db: Session,
    ) -> dict:
        """Send an SMS confirmation after a successful payment webhook."""
        message = (
            f"AgroOS: Payment of GHS {amount:.2f} received. Ref: {reference}. "
            f"Your Trust Score has been updated. Thank you!"
        )
        result = await self.moolre.send_single_sms(
            phone=farmer.phone,
            message=message,
            ref=reference,
        )
        log = self._log(
            db=db,
            message_type=MessageType.sms,
            cooperative_id=farmer.cooperative_id,
            recipients_count=1,
            body=message,
            moolre_ref=reference,
            status="sent" if result["success"] else "failed",
        )
        return {"success": result["success"], "log_id": log.id}

    async def send_loan_repayment_reminder(
        self,
        *,
        loan: Loan,
        farmer: Farmer,
        reminder_kind: str,
        scheduled_for: date,
        db: Session,
        manual: bool = False,
        sent_by: str | None = None,
    ) -> LoanReminder:
        """Send an idempotent reminder without initiating a payment."""
        existing = (
            db.query(LoanReminder)
            .filter(
                LoanReminder.loan_id == loan.id,
                LoanReminder.reminder_kind == reminder_kind,
                LoanReminder.scheduled_for == scheduled_for,
            )
            .first()
        )
        if existing and existing.status == "sent":
            return existing
        reminder = existing or LoanReminder(
            loan_id=loan.id,
            reminder_kind=reminder_kind,
            scheduled_for=scheduled_for,
            status="pending",
            manual=manual,
        )
        if not existing:
            db.add(reminder)
            db.commit()
            db.refresh(reminder)

        from app.config import get_settings

        ussd_code = get_settings().agroos_ussd_code.strip() or "*919*4020#"
        due_date = (
            loan.expected_repayment_date.strftime("%d %b %Y")
            if loan.expected_repayment_date
            else "the agreed date"
        )
        message = (
            f"AgroOS: Loan #{loan.id} repayment of GHS {loan.amount:.2f} is due "
            f"{due_date}. Dial {ussd_code} and choose Repay Loan. Never share your OTP."
        )
        reminder.attempts += 1
        result = await self.moolre.send_single_sms(
            phone=farmer.phone,
            message=message,
            ref=f"loan-reminder-{loan.id}-{scheduled_for.isoformat()}-{reminder_kind}",
        )
        reminder.status = "sent" if result["success"] else "failed"
        reminder.sent_at = datetime.utcnow() if result["success"] else None
        reminder.error = None if result["success"] else result.get("message")
        provider_ref = result.get("raw", {}).get("data")
        reminder.provider_reference = str(provider_ref) if provider_ref else None
        self._log(
            db=db,
            message_type=MessageType.sms,
            cooperative_id=farmer.cooperative_id,
            recipients_count=1,
            body=message,
            moolre_ref=reminder.provider_reference,
            sent_by=sent_by,
            status=reminder.status,
        )
        db.commit()
        db.refresh(reminder)
        return reminder

    async def send_payment_action_required(
        self,
        farmer: Farmer,
        amount: float,
        reference: str,
        db: Session,
        sent_by: str | None = None,
    ) -> dict:
        """Tell the payer how to resume an OTP-gated request on their phone."""
        from app.config import get_settings

        ussd_code = get_settings().agroos_ussd_code.strip() or "*919*4020#"
        message = (
            f"AgroOS: Complete your GHS {amount:.2f} payment on your phone. "
            f"Dial {ussd_code} and choose Complete Pending Payment. "
            "Never share your OTP with cooperative staff."
        )
        result = await self.moolre.send_single_sms(
            phone=farmer.phone,
            message=message,
            ref=reference,
        )
        log = self._log(
            db=db,
            message_type=MessageType.sms,
            cooperative_id=farmer.cooperative_id,
            recipients_count=1,
            body=message,
            moolre_ref=reference,
            sent_by=sent_by,
            status="sent" if result["success"] else "failed",
        )
        return {"success": result["success"], "log_id": log.id}

    async def broadcast_to_cooperative(
        self,
        cooperative_id: int,
        message: str,
        db: Session,
        sent_by: str | None = None,
        active_only: bool = True,
    ) -> dict:
        """
        Send a bulk SMS to all (active) members of a cooperative.
        Returns total recipients, successes, and failures.
        """
        from app.models.models import CooperativeMembership as Farmer
        from app.models.models import MembershipStatus

        query = db.query(Farmer).filter(Farmer.cooperative_id == cooperative_id)
        if active_only:
            query = query.filter(Farmer.membership_status == MembershipStatus.active)

        farmers = query.all()
        if not farmers:
            return {"success": True, "recipients_count": 0, "message": "No active members found."}

        recipients = [
            {"recipient": f.phone, "message": message, "ref": str(uuid.uuid4())}
            for f in farmers
        ]

        result = await self.moolre.send_sms(recipients)

        log = self._log(
            db=db,
            message_type=MessageType.sms,
            cooperative_id=cooperative_id,
            recipients_count=len(farmers),
            body=message,
            sent_by=sent_by,
            moolre_ref=result.get("moolre_ref"),
            status="sent" if result["success"] else "partial_fail",
        )

        return {
            "success": result["success"],
            "recipients_count": len(farmers),
            "message": result["message"],
            "log_id": log.id,
        }

    async def send_dues_reminder_to_cooperative(
        self,
        cooperative_id: int,
        amount: float,
        due_date: str,
        db: Session,
        sent_by: str | None = None,
    ) -> dict:
        """
        Send dues reminder to ALL active members of a cooperative in one call.
        """
        from app.config import get_settings
        from app.models.models import CooperativeMembership as Farmer
        from app.models.models import MembershipStatus

        settings = get_settings()
        ussd_code = settings.agroos_ussd_code.strip() or "*919*4020#"

        farmers = (
            db.query(Farmer)
            .filter(
                Farmer.cooperative_id == cooperative_id,
                Farmer.membership_status == MembershipStatus.active,
            )
            .all()
        )
        if not farmers:
            return {"success": True, "recipients_count": 0, "message": "No active members."}

        recipients = [
            {
                "recipient": f.phone,
                "message": (
                    f"Dear {f.name}, your cooperative dues of GHS {amount:.2f} are due by {due_date}. "
                    f"Dial {ussd_code} and choose Pay Dues. - AgroOS"
                ),
                "ref": str(uuid.uuid4()),
            }
            for f in farmers
        ]

        result = await self.moolre.send_sms(recipients)

        log = self._log(
            db=db,
            message_type=MessageType.sms,
            cooperative_id=cooperative_id,
            recipients_count=len(farmers),
            body=f"Dues reminder: GHS {amount:.2f} due by {due_date}",
            sent_by=sent_by,
            moolre_ref=result.get("moolre_ref"),
            status="sent" if result["success"] else "partial_fail",
        )

        return {
            "success": result["success"],
            "recipients_count": len(farmers),
            "message": result["message"],
            "log_id": log.id,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _log(
        self,
        db: Session,
        message_type: MessageType,
        cooperative_id: int | None,
        recipients_count: int,
        body: str,
        moolre_ref: str | None = None,
        sent_by: str | None = None,
        status: str = "sent",
    ) -> CommunicationLog:
        """Persist a CommunicationLog record and return it."""
        log = CommunicationLog(
            message_type=message_type,
            cooperative_id=cooperative_id,
            recipients_count=recipients_count,
            body=body,
            moolre_ref=moolre_ref,
            sent_by=sent_by,
            status=status,
            sent_at=datetime.utcnow(),
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log
