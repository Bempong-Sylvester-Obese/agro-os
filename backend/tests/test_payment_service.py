from app.domain.payment_event import PaymentEvent
from app.models.models import Transaction, TransactionStatus, TransactionType
from app.services.payment_service import process_payment_event


def test_payment_event_maps_success_before_duplicate_check(db, farmer) -> None:
    tx = Transaction(
        farmer_id=farmer["id"],
        transaction_type=TransactionType.dues,
        amount=20,
        status=TransactionStatus.completed,
        moolre_reference="domain-duplicate-ref",
    )
    db.add(tx)
    db.commit()
    event = PaymentEvent(
        provider="moolre",
        event_type="payment",
        external_ref="domain-duplicate-ref",
        amount=20,
        currency="GHS",
        status="success",
        metadata={},
    )

    result = process_payment_event(event, db)

    assert result == {"status": "duplicate", "transaction_id": tx.id}
    db.refresh(tx)
    assert tx.status == TransactionStatus.completed
