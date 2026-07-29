from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.career_plans.evaluation import (  # noqa: E402
    evaluate_career_plan_agent,
    format_career_plan_evaluation_report,
)


def main() -> int:
    report = evaluate_career_plan_agent()
    print(format_career_plan_evaluation_report(report))
    print("\nJSON report:")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
