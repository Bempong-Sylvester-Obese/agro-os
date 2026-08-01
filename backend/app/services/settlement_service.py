"""Exact, auditable farmer settlement calculation and payout orchestration."""

import json
from datetime import datetime
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.models import (
    AdminAuditLog,
    BuyerPaymentReceipt,
    DisbursementBatch,
    DisbursementBatchStatus,
    Loan,
    LoanStatus,
    ProduceIntake,
    ProduceSale,
    ProduceSaleStatus,
    ReceiptStatus,
    SettlementDeduction,
    SettlementDeductionType,
    SettlementLine,
    SettlementLineStatus,
    SettlementRun,
    SettlementStatus,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from app.schemas.market import SettlementCalculate
from app.services.moolre_service import MoolreService

CENT = Decimal("0.01")
KG = Decimal("0.001")


def money(value: Decimal | int | str) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def _allocate(total: Decimal, weights: list[Decimal]) -> list[Decimal]:
    """Allocate money exactly, assigning rounding residue to the last weight."""
    total = money(total)
    weight_total = sum(weights, Decimal("0"))
    if not weights:
        return []
    if total == 0 or weight_total == 0:
        return [Decimal("0.00") for _ in weights]
    allocated: list[Decimal] = []
    remaining = total
    for index, weight in enumerate(weights):
        if index == len(weights) - 1:
            share = remaining
        else:
            share = (total * weight / weight_total).quantize(
                CENT, rounding=ROUND_DOWN
            )
            remaining -= share
        allocated.append(money(share))
    return allocated


def _actor_id(user) -> str:
    return str(user.id) if user is not None else "system"


def _audit(
    db: Session,
    *,
    cooperative_id: int,
    actor_id: str,
    action: str,
    resource_type: str,
    resource_id: int,
    details: str | None = None,
) -> None:
    db.add(
        AdminAuditLog(
            cooperative_id=cooperative_id,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            details=details,
        )
    )


class SettlementService:
    @staticmethod
    def load(db: Session, settlement_id: int, cooperative_id: int) -> SettlementRun:
        settlement = (
            db.query(SettlementRun)
            .options(
                joinedload(SettlementRun.lines).joinedload(
                    SettlementLine.deductions
                )
            )
            .filter(
                SettlementRun.id == settlement_id,
                SettlementRun.cooperative_id == cooperative_id,
            )
            .first()
        )
        if not settlement:
            raise HTTPException(status_code=404, detail="Settlement not found")
        return settlement

    @staticmethod
    def calculate(
        db: Session,
        *,
        sale_id: int,
        cooperative_id: int,
        config: SettlementCalculate,
        actor,
    ) -> SettlementRun:
        sale = (
            db.query(ProduceSale)
            .filter(
                ProduceSale.id == sale_id,
                ProduceSale.cooperative_id == cooperative_id,
            )
            .with_for_update()
            .first()
        )
        if not sale:
            raise HTTPException(status_code=404, detail="Sale not found")
        if sale.status not in (
            ProduceSaleStatus.confirmed,
            ProduceSaleStatus.funded,
        ):
            raise HTTPException(
                status_code=409,
                detail="Only a confirmed sale can be settled",
            )
        if (
            db.query(SettlementRun)
            .filter(
                SettlementRun.sale_id == sale.id,
                SettlementRun.status != SettlementStatus.completed,
            )
            .first()
        ):
            raise HTTPException(
                status_code=409,
                detail="An active settlement already exists for this sale",
            )

        verified = money(
            db.query(func.coalesce(func.sum(BuyerPaymentReceipt.amount), 0))
            .filter(
                BuyerPaymentReceipt.sale_id == sale.id,
                BuyerPaymentReceipt.status == ReceiptStatus.verified,
            )
            .scalar()
        )
        gross_total = money(sale.gross_amount)
        if verified < gross_total:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Verified buyer funds are insufficient: "
                    f"GHS {verified:.2f} verified of GHS {gross_total:.2f}"
                ),
            )

        intakes = (
            db.query(ProduceIntake)
            .filter(
                ProduceIntake.aggregation_batch_id == sale.aggregation_batch_id,
                ProduceIntake.cooperative_id == cooperative_id,
            )
            .order_by(ProduceIntake.id)
            .with_for_update()
            .all()
        )
        if not intakes:
            raise HTTPException(status_code=409, detail="Sale batch has no intakes")

        by_member: dict[int, Decimal] = {}
        for intake in intakes:
            quantity = Decimal(str(intake.net_quantity_kg or intake.quantity_kg))
            by_member[intake.membership_id] = (
                by_member.get(intake.membership_id, Decimal("0")) + quantity
            )
        member_ids = sorted(by_member)
        intake_weights = [by_member[member_id] for member_id in member_ids]
        total_intake = sum(intake_weights, Decimal("0"))
        sold_quantity = Decimal(str(sale.quantity_kg))
        line_quantities = [
            (sold_quantity * weight / total_intake).quantize(
                KG, rounding=ROUND_HALF_UP
            )
            for weight in intake_weights
        ]
        quantity_delta = sold_quantity - sum(line_quantities, Decimal("0"))
        line_quantities[-1] += quantity_delta
        gross_allocations = _allocate(gross_total, intake_weights)
        transport_allocations = _allocate(
            Decimal(config.transport_total), gross_allocations
        )
        quality_allocations = _allocate(
            Decimal(config.quality_total), gross_allocations
        )

        manual_by_member: dict[int, list] = {}
        for item in config.manual_deductions:
            if item.membership_id not in by_member:
                raise HTTPException(
                    status_code=422,
                    detail=f"Membership {item.membership_id} has no intake in this sale",
                )
            manual_by_member.setdefault(item.membership_id, []).append(item)

        snapshot = {
            "version": 1,
            "sale_id": sale.id,
            "batch_id": sale.aggregation_batch_id,
            "sale_quantity_kg": str(sold_quantity),
            "unit_price": str(money(sale.unit_price)),
            "gross_total": str(gross_total),
            "verified_funds_total": str(verified),
            "config": {
                "cooperative_fee_percent": str(config.cooperative_fee_percent),
                "transport_total": str(money(config.transport_total)),
                "quality_total": str(money(config.quality_total)),
                "deduct_outstanding_loans": config.deduct_outstanding_loans,
                "manual_deductions": [
                    {
                        "membership_id": item.membership_id,
                        "amount": str(money(item.amount)),
                        "description": item.description,
                    }
                    for item in config.manual_deductions
                ],
            },
            "intakes": [
                {
                    "id": intake.id,
                    "membership_id": intake.membership_id,
                    "gross_quantity_kg": str(intake.quantity_kg),
                    "net_quantity_kg": str(
                        intake.net_quantity_kg or intake.quantity_kg
                    ),
                    "quality_grade": intake.quality_grade,
                }
                for intake in intakes
            ],
        }
        settlement = SettlementRun(
            cooperative_id=cooperative_id,
            sale_id=sale.id,
            currency=sale.currency,
            cooperative_fee_percent=config.cooperative_fee_percent,
            transport_total=money(config.transport_total),
            quality_total=money(config.quality_total),
            gross_total=gross_total,
            verified_funds_total=verified,
            deductions_total=Decimal("0.00"),
            net_total=Decimal("0.00"),
            snapshot_json=json.dumps(snapshot, sort_keys=True, separators=(",", ":")),
            calculated_by=_actor_id(actor),
        )
        db.add(settlement)
        db.flush()

        total_deductions = Decimal("0.00")
        total_net = Decimal("0.00")
        fee_rate = Decimal(config.cooperative_fee_percent) / Decimal("100")
        for index, member_id in enumerate(member_ids):
            gross = gross_allocations[index]
            remaining = gross
            deduction_specs: list[
                tuple[SettlementDeductionType, Decimal, str, int | None]
            ] = []

            def add_deduction(
                kind: SettlementDeductionType,
                requested: Decimal,
                description: str,
                loan_id: int | None = None,
            ) -> None:
                nonlocal remaining
                applied = min(money(requested), remaining)
                if applied > 0:
                    deduction_specs.append((kind, applied, description, loan_id))
                    remaining = money(remaining - applied)

            add_deduction(
                SettlementDeductionType.cooperative_fee,
                gross * fee_rate,
                f"Cooperative fee ({config.cooperative_fee_percent}%)",
            )
            add_deduction(
                SettlementDeductionType.transport,
                transport_allocations[index],
                "Allocated transport cost",
            )
            add_deduction(
                SettlementDeductionType.quality,
                quality_allocations[index],
                "Quality adjustment",
            )
            for manual in manual_by_member.get(member_id, []):
                add_deduction(
                    SettlementDeductionType.manual,
                    Decimal(manual.amount),
                    manual.description,
                )
            if config.deduct_outstanding_loans and remaining > 0:
                loans = (
                    db.query(Loan)
                    .filter(
                        Loan.farmer_id == member_id,
                        Loan.status == LoanStatus.disbursed,
                    )
                    .order_by(Loan.id)
                    .with_for_update()
                    .all()
                )
                for loan in loans:
                    loan_amount = money(Decimal(str(loan.amount)))
                    if remaining >= loan_amount:
                        add_deduction(
                            SettlementDeductionType.loan,
                            loan_amount,
                            f"Outstanding loan #{loan.id}",
                            loan.id,
                        )

            line_deductions = money(gross - remaining)
            line = SettlementLine(
                settlement_run_id=settlement.id,
                membership_id=member_id,
                quantity_kg=line_quantities[index],
                unit_price=money(sale.unit_price),
                gross_amount=gross,
                deductions_total=line_deductions,
                net_amount=remaining,
                status=(
                    SettlementLineStatus.paid
                    if remaining == 0
                    else SettlementLineStatus.pending
                ),
                payout_reference=f"settlement-{settlement.id}-{member_id}",
            )
            db.add(line)
            db.flush()
            for kind, amount, description, loan_id in deduction_specs:
                db.add(
                    SettlementDeduction(
                        settlement_line_id=line.id,
                        deduction_type=kind,
                        amount=amount,
                        description=description,
                        loan_id=loan_id,
                    )
                )
            total_deductions += line_deductions
            total_net += remaining

        settlement.deductions_total = money(total_deductions)
        settlement.net_total = money(total_net)
        _audit(
            db,
            cooperative_id=cooperative_id,
            actor_id=_actor_id(actor),
            action="settlement.calculated",
            resource_type="settlement",
            resource_id=settlement.id,
            details=f"gross={gross_total};deductions={total_deductions};net={total_net}",
        )
        db.commit()
        return SettlementService.load(db, settlement.id, cooperative_id)

    @staticmethod
    async def disburse(
        db: Session,
        *,
        settlement_id: int,
        cooperative_id: int,
        actor,
        retry_failed: bool = False,
    ) -> tuple[SettlementRun, DisbursementBatch, list[int]]:
        settlement = (
            db.query(SettlementRun)
            .filter(
                SettlementRun.id == settlement_id,
                SettlementRun.cooperative_id == cooperative_id,
            )
            .with_for_update()
            .first()
        )
        if not settlement:
            raise HTTPException(status_code=404, detail="Settlement not found")
        if settlement.status not in (
            SettlementStatus.approved,
            SettlementStatus.partially_paid,
        ):
            raise HTTPException(
                status_code=409,
                detail="Only approved or partially paid settlements can be disbursed",
            )
        previous_batches = (
            db.query(DisbursementBatch)
            .filter(DisbursementBatch.settlement_run_id == settlement.id)
            .count()
        )
        if retry_failed and previous_batches == 0:
            raise HTTPException(
                status_code=409,
                detail="Initial payout must use the disburse endpoint",
            )
        if not retry_failed and previous_batches > 0:
            raise HTTPException(
                status_code=409,
                detail="Use retry-failed to retry a previous payout batch",
            )
        eligible_status = (
            SettlementLineStatus.failed
            if retry_failed
            else SettlementLineStatus.pending
        )
        lines = (
            db.query(SettlementLine)
            .filter(
                SettlementLine.settlement_run_id == settlement.id,
                SettlementLine.status == eligible_status,
                SettlementLine.net_amount > 0,
            )
            .order_by(SettlementLine.id)
            .with_for_update()
            .all()
        )
        if not lines:
            raise HTTPException(
                status_code=409,
                detail=(
                    "No unpaid lines are eligible"
                    if previous_batches == 0
                    else "No failed lines are eligible for retry"
                ),
            )
        attempt = previous_batches + 1
        batch = DisbursementBatch(
            settlement_run_id=settlement.id,
            status=DisbursementBatchStatus.processing,
            attempt_number=attempt,
            created_by=_actor_id(actor),
            started_at=datetime.utcnow(),
        )
        db.add(batch)
        db.flush()
        transactions: list[tuple[SettlementLine, Transaction]] = []
        for line in lines:
            external_ref = (
                f"{settlement.id % 10000:04d}"
                f"{line.id % 10000:04d}{attempt % 10000:04d}"
            )
            tx = Transaction(
                farmer_id=line.membership_id,
                settlement_line_id=line.id,
                disbursement_batch_id=batch.id,
                transaction_type=TransactionType.settlement_payout,
                amount=line.net_amount,
                currency=settlement.currency,
                status=TransactionStatus.pending,
                moolre_reference=external_ref,
                payee_phone=line.membership.phone,
                description=f"Settlement #{settlement.id} line #{line.id}",
            )
            line.status = SettlementLineStatus.processing
            line.last_error = None
            db.add(tx)
            transactions.append((line, tx))
        settlement.status = SettlementStatus.processing
        _audit(
            db,
            cooperative_id=cooperative_id,
            actor_id=_actor_id(actor),
            action="settlement.disbursement_started",
            resource_type="disbursement_batch",
            resource_id=batch.id,
            details=f"attempt={attempt};lines={len(lines)}",
        )
        db.commit()

        moolre = MoolreService()
        account_number, wallet_error = await moolre.resolve_verified_account(None)
        for original_line, original_tx in transactions:
            db.refresh(original_tx)
            if wallet_error:
                result = {"success": False, "message": wallet_error}
            else:
                try:
                    result = await moolre.initiate_transfer(
                        receiver_phone=original_tx.payee_phone,
                        amount=original_tx.amount,
                        currency=original_tx.currency,
                        external_ref=original_tx.moolre_reference,
                        reference=f"AgroOS settlement #{settlement.id}",
                        account_number=account_number,
                    )
                except Exception:
                    # The provider may have accepted an idempotent external
                    # reference before the connection failed. Keep it pending
                    # for reconciliation instead of creating a duplicate.
                    continue
            db.expire_all()
            tx = (
                db.query(Transaction)
                .filter(Transaction.id == original_tx.id)
                .with_for_update()
                .one()
            )
            line = (
                db.query(SettlementLine)
                .filter(SettlementLine.id == original_line.id)
                .with_for_update()
                .one()
            )
            if result.get("success"):
                tx.moolre_transfer_ref = (
                    result.get("moolre_transfer_ref") or tx.moolre_reference
                )
                line.status = SettlementLineStatus.processing
            else:
                tx.status = TransactionStatus.failed
                line.status = SettlementLineStatus.failed
                line.last_error = result.get("message") or "Transfer initiation failed"
            db.commit()

        settlement, batch = SettlementService._refresh_rollups(
            db, settlement.id, batch.id
        )
        return (
            SettlementService.load(db, settlement.id, cooperative_id),
            batch,
            [line.id for line, _ in transactions],
        )

    @staticmethod
    def _refresh_rollups(
        db: Session, settlement_id: int, batch_id: int
    ) -> tuple[SettlementRun, DisbursementBatch]:
        settlement = (
            db.query(SettlementRun)
            .filter(SettlementRun.id == settlement_id)
            .with_for_update()
            .one()
        )
        batch = (
            db.query(DisbursementBatch)
            .filter(DisbursementBatch.id == batch_id)
            .with_for_update()
            .one()
        )
        lines = (
            db.query(SettlementLine)
            .filter(SettlementLine.settlement_run_id == settlement_id)
            .all()
        )
        statuses = {line.status for line in lines}
        if statuses == {SettlementLineStatus.paid}:
            settlement.status = SettlementStatus.completed
            settlement.completed_at = datetime.utcnow()
        elif SettlementLineStatus.failed in statuses:
            settlement.status = SettlementStatus.partially_paid
        else:
            settlement.status = SettlementStatus.processing

        batch_transactions = (
            db.query(Transaction)
            .filter(Transaction.disbursement_batch_id == batch_id)
            .all()
        )
        tx_statuses = {tx.status for tx in batch_transactions}
        if tx_statuses == {TransactionStatus.completed}:
            batch.status = DisbursementBatchStatus.completed
            batch.completed_at = datetime.utcnow()
        elif TransactionStatus.failed in tx_statuses:
            batch.status = DisbursementBatchStatus.partially_failed
            batch.completed_at = datetime.utcnow()
        else:
            batch.status = DisbursementBatchStatus.processing
        db.commit()
        return settlement, batch

    @staticmethod
    async def reconcile(
        db: Session,
        *,
        settlement_id: int,
        cooperative_id: int,
        actor,
    ) -> tuple[SettlementRun, list[int]]:
        settlement = SettlementService.load(db, settlement_id, cooperative_id)
        pending = (
            db.query(Transaction)
            .join(SettlementLine, Transaction.settlement_line_id == SettlementLine.id)
            .filter(
                SettlementLine.settlement_run_id == settlement.id,
                Transaction.status == TransactionStatus.pending,
            )
            .order_by(Transaction.id)
            .all()
        )
        if not pending:
            return settlement, []
        moolre = MoolreService()
        account_number, wallet_error = await moolre.resolve_verified_account(None)
        if wallet_error:
            raise HTTPException(status_code=502, detail=wallet_error)
        reconciled: list[int] = []
        batch_ids: set[int] = set()
        for pending_tx in pending:
            result = await moolre.transfer_status(
                reference=(
                    pending_tx.moolre_transfer_ref
                    or pending_tx.moolre_reference
                ),
                account_number=account_number,
                id_type="2" if pending_tx.moolre_transfer_ref else "1",
            )
            db.expire_all()
            tx = (
                db.query(Transaction)
                .filter(Transaction.id == pending_tx.id)
                .with_for_update()
                .one()
            )
            line = (
                db.query(SettlementLine)
                .filter(SettlementLine.id == tx.settlement_line_id)
                .with_for_update()
                .one()
            )
            if tx.status != TransactionStatus.pending:
                continue
            if result.get("status") == "completed":
                provider_amount = money(result.get("amount") or tx.amount)
                if provider_amount != money(tx.amount):
                    line.last_error = "Provider amount mismatch"
                    continue
                tx.status = TransactionStatus.completed
                line.status = SettlementLineStatus.paid
                line.paid_at = datetime.utcnow()
                line.last_error = None
                loan_deductions = (
                    db.query(SettlementDeduction)
                    .filter(
                        SettlementDeduction.settlement_line_id == line.id,
                        SettlementDeduction.deduction_type
                        == SettlementDeductionType.loan,
                        SettlementDeduction.loan_id.is_not(None),
                    )
                    .all()
                )
                for deduction in loan_deductions:
                    loan = (
                        db.query(Loan)
                        .filter(
                            Loan.id == deduction.loan_id,
                            Loan.status == LoanStatus.disbursed,
                        )
                        .with_for_update()
                        .first()
                    )
                    if loan and money(deduction.amount) == money(loan.amount):
                        loan.status = LoanStatus.repaid
                        loan.repaid_at = datetime.utcnow()
                reconciled.append(line.id)
            elif result.get("status") == "failed":
                tx.status = TransactionStatus.failed
                line.status = SettlementLineStatus.failed
                line.last_error = "Provider marked transfer failed"
                reconciled.append(line.id)
            if tx.disbursement_batch_id:
                batch_ids.add(tx.disbursement_batch_id)
            db.commit()
        for batch_id in batch_ids:
            SettlementService._refresh_rollups(db, settlement.id, batch_id)
        _audit(
            db,
            cooperative_id=cooperative_id,
            actor_id=_actor_id(actor),
            action="settlement.reconciled",
            resource_type="settlement",
            resource_id=settlement.id,
            details=f"lines={','.join(map(str, reconciled))}",
        )
        db.commit()
        return SettlementService.load(db, settlement.id, cooperative_id), reconciled
