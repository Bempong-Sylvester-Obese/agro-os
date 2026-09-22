#!/usr/bin/env python3
"""CLI: purge Golden Path demo data from the configured DATABASE_URL.

Production guard
----------------
When ``APP_ENV`` is ``production``/``prod`` (any casing) a destructive run is
refused unless ``--allow-production`` is passed explicitly. ``--dry-run`` is
always permitted so operators can inspect what would be removed first.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_settings
from app.database.db import create_session
from app.database.purge_demo import purge_demo_cooperative

EXIT_REFUSED_IN_PRODUCTION = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Purge Kuapa Kokoo demo cooperative data")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be deleted without changing the database",
    )
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help=(
            "Required to run a destructive purge when APP_ENV=production. "
            "Without it the script refuses and exits with status 2."
        ),
    )
    return parser


def production_guard(*, is_production: bool, dry_run: bool, allow_production: bool) -> str | None:
    """Return a refusal message when a destructive purge is not permitted."""
    if is_production and not dry_run and not allow_production:
        return (
            "Refusing to purge demo data: APP_ENV is production. Re-run with "
            "--dry-run to preview, or --allow-production to confirm the deletion."
        )
    return None


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    refusal = production_guard(
        is_production=get_settings().is_production,
        dry_run=args.dry_run,
        allow_production=args.allow_production,
    )
    if refusal:
        print(f"[REFUSED] {refusal}", file=sys.stderr)
        return EXIT_REFUSED_IN_PRODUCTION

    db = create_session()
    try:
        result = purge_demo_cooperative(db, dry_run=args.dry_run)
    finally:
        db.close()

    mode = "DRY RUN" if args.dry_run else "PURGED" if result.get("deleted") else "SKIPPED"
    print(f"[{mode}] {result}")
    return 0 if result.get("deleted") or result.get("dry_run") or result.get("reason") else 1


if __name__ == "__main__":
    raise SystemExit(main())
