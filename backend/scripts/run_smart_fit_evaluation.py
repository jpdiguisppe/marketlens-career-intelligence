from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.analysis.evaluation import (  # noqa: E402
    evaluate_smart_fit_benchmark,
    format_smart_fit_evaluation_report,
    load_smart_fit_benchmark,
)
from app.analysis.role_aware_stable import analyze_smart_fit  # noqa: E402


def _validate_case_execution() -> bool:
    passed = True
    for case in load_smart_fit_benchmark()["cases"]:
        try:
            analyze_smart_fit(
                resume_text=case["resume_text"],
                job_description=case["job_description"],
                use_model_assisted=bool(case.get("use_model_assisted", False)),
            )
        except Exception:  # pragma: no cover - diagnostic CLI boundary
            passed = False
            print(f"Case execution failed: {case['id']}")
            traceback.print_exc()
    return passed


def main() -> int:
    if not _validate_case_execution():
        return 1

    report = evaluate_smart_fit_benchmark()
    print(format_smart_fit_evaluation_report(report))
    print("\nJSON report:")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
