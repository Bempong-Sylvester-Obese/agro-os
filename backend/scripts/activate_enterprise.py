#!/usr/bin/env python3
"""CLI: activate, extend, or end an Enterprise organization contract (#237).

Enterprise pricing is contracted ("Annual agreement"), so the subscription on
an ``organizations`` row is never set through the API. Operators run this
after a signed agreement:

    python scripts/activate_enterprise.py --org 12 --months 12 --contract ENT-2026-004
    python scripts/activate_enterprise.py --org 12 --cancel

While the organization's subscription is active, every member cooperative
inherits the Enterprise plan as its effective plan (see docs/billing.md).
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database.db import create_session  # noqa: E402
from app.models.models import Organization  # noqa: E402

EXIT_NOT_FOUND = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage an Enterprise organization contract")
    parser.add_argument("--org", type=int, required=True, help="organizations.id")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--months", type=int, default=12, help="Contract length from now (default 12)")
    group.add_argument("--cancel", action="store_true", help="End the contract now (status=cancelled)")
    parser.add_argument("--contract", help="Contract / agreement reference to record")
    parser.add_argument("--plan", default="enterprise", help="Plan key to grant (default enterprise)")
    return parser


def apply(org: Organization, *, months: int, cancel: bool, contract: str | None, plan: str, now: datetime | None = None) -> str:
    """Mutate ``org`` in place and return a one-line summary."""
    now = now or datetime.utcnow()
    if cancel:
        org.subscription_status = Organization.STATUS_CANCELLED
        org.subscription_expires_at = now
        return f"organization {org.id} ({org.name}): contract cancelled"
    if months <= 0:
        raise ValueError("--months must be positive")
    org.subscription_plan = plan
    org.subscription_status = Organization.STATUS_ACTIVE
    org.subscription_expires_at = now + timedelta(days=30 * months)
    if contract:
        org.contract_reference = contract
    return (
        f"organization {org.id} ({org.name}): {plan} active until "
        f"{org.subscription_expires_at:%Y-%m-%d}"
        + (f" [contract {contract}]" if contract else "")
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    db = create_session()
    try:
        org = db.get(Organization, args.org)
        if org is None:
            print(f"organization {args.org} not found", file=sys.stderr)
            return EXIT_NOT_FOUND
        summary = apply(org, months=args.months, cancel=args.cancel, contract=args.contract, plan=args.plan)
        db.commit()
        print(summary)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
