#!/usr/bin/env python3
"""CLI: purge Golden Path demo data from the configured DATABASE_URL."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database.db import create_session
from app.database.purge_demo import purge_demo_cooperative


def main() -> int:
    parser = argparse.ArgumentParser(description="Purge Kuapa Kokoo demo cooperative data")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be deleted without changing the database",
    )
    args = parser.parse_args()

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
