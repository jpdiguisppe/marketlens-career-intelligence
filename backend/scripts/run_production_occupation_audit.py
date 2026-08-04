from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.production_canary import DEFAULT_BACKEND_URL  # noqa: E402
from app.production_occupation_audit import (  # noqa: E402
    ProductionOccupationAudit,
    ProductionOccupationAuditError,
    format_production_occupation_audit_report,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the bounded MarketLens production occupation audit."
    )
    parser.add_argument(
        "--backend-url",
        default=os.getenv("MARKETLENS_BACKEND_URL", DEFAULT_BACKEND_URL),
    )
    parser.add_argument(
        "--expected-revision",
        default=os.getenv("EXPECTED_REVISION"),
    )
    parser.add_argument(
        "--wait-seconds",
        type=float,
        default=float(os.getenv("AUDIT_WAIT_SECONDS", "0")),
    )
    parser.add_argument(
        "--inter-request-seconds",
        type=float,
        default=float(os.getenv("AUDIT_INTER_REQUEST_SECONDS", "2.25")),
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    audit = ProductionOccupationAudit(
        backend_url=args.backend_url,
        expected_revision=args.expected_revision,
        inter_request_seconds=args.inter_request_seconds,
    )
    try:
        try:
            audit.wait_for_exact_revision(wait_seconds=args.wait_seconds)
        except ProductionOccupationAuditError as exc:
            print(f"Revision wait failed safely: {exc.code}")
            return 1
        audit.run()
        report = audit.report()
        print(format_production_occupation_audit_report(report))
        print("\nJSON report:")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["passed"] else 1
    finally:
        audit.close()


if __name__ == "__main__":
    raise SystemExit(main())
