"""Payment domain service — processes normalized PaymentEvents."""
from app.domain.payment_event import PaymentEvent


def process_payment_event(event: PaymentEvent, db):
    """Process a normalized payment event against the ledger.

    This is the domain logic extracted from webhooks.py's _process_payment_payload.
    The service receives normalized events, not raw Moolre payloads.

    For now this delegates to the existing webhook handler. In future milestones
    the flow will be: webhook handler normalizes → this service processes.
    """
    pass
