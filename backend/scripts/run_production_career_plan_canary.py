from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.production_canary import (  # noqa: E402
    DEFAULT_BACKEND_URL,
    DEFAULT_FRONTEND_URL,
    ProductionCareerPlanCanary,
    ProductionCanaryError,
    format_production_canary_report,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the MarketLens production Career Plan canary.")
    parser.add_argument("--frontend-url", default=os.getenv("MARKETLENS_FRONTEND_URL", DEFAULT_FRONTEND_URL))
    parser.add_argument("--backend-url", default=os.getenv("MARKETLENS_BACKEND_URL", DEFAULT_BACKEND_URL))
    parser.add_argument("--expected-revision", default=os.getenv("EXPECTED_REVISION"))
    parser.add_argument("--mode", choices=("public", "full"), default=os.getenv("CANARY_MODE", "public"))
    parser.add_argument("--run-model", action="store_true", default=os.getenv("RUN_MODEL_CANARY", "").lower() == "true")
    parser.add_argument("--skip-cancellation", action="store_true")
    parser.add_argument("--wait-seconds", type=float, default=float(os.getenv("CANARY_WAIT_SECONDS", "0")))
    return parser


def main() -> int:
    args = _parser().parse_args()
    token = (os.getenv("MARKETLENS_CANARY_BEARER_TOKEN") or "").strip()
    second_token = (os.getenv("MARKETLENS_CANARY_SECOND_BEARER_TOKEN") or "").strip() or None
    canary = ProductionCareerPlanCanary(
        frontend_url=args.frontend_url,
        backend_url=args.backend_url,
        expected_revision=args.expected_revision,
    )
    try:
        try:
            canary.wait_for_exact_revision(wait_seconds=args.wait_seconds)
        except ProductionCanaryError as exc:
            print(f"Revision wait failed safely: {exc.code}")
            return 1

        canary.run_public(run_model=args.run_model)
        authenticated_configured = bool(token)
        if args.mode == "full" and authenticated_configured:
            canary.run_authenticated(
                token=token,
                second_token=second_token,
                run_model=args.run_model,
                test_cancellation=not args.skip_cancellation,
            )
        report = canary.report(mode=args.mode, authenticated_configured=authenticated_configured)
        print(format_production_canary_report(report))
        print("\nJSON report:")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["passed"] else 1
    finally:
        canary.close()


if __name__ == "__main__":
    raise SystemExit(main())
