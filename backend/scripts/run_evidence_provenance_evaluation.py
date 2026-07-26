from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.analysis.provenance_evaluation import (  # noqa: E402
    evaluate_evidence_provenance,
    format_evidence_provenance_report,
)


def main() -> int:
    report = evaluate_evidence_provenance()
    print(format_evidence_provenance_report(report))
    print("\nJSON report:")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
