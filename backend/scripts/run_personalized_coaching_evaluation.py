from app.analysis.coaching_evaluation import (
    evaluate_personalized_coaching,
    format_personalized_coaching_report,
)


def main() -> int:
    report = evaluate_personalized_coaching()
    print(format_personalized_coaching_report(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
