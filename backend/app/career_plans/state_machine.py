from app.career_plans.schemas import CareerPlanRunStatus


class InvalidCareerPlanTransition(ValueError):
    pass


_ALLOWED_TRANSITIONS: dict[CareerPlanRunStatus, set[CareerPlanRunStatus]] = {
    CareerPlanRunStatus.DRAFT: {CareerPlanRunStatus.RUNNING},
    CareerPlanRunStatus.RUNNING: {
        CareerPlanRunStatus.AWAITING_APPROVAL,
        CareerPlanRunStatus.CANCELLED,
        CareerPlanRunStatus.FAILED,
    },
    CareerPlanRunStatus.FAILED: {CareerPlanRunStatus.RUNNING},
    CareerPlanRunStatus.CANCELLED: {CareerPlanRunStatus.RUNNING},
    CareerPlanRunStatus.AWAITING_APPROVAL: {
        CareerPlanRunStatus.APPROVED,
        CareerPlanRunStatus.REJECTED,
        CareerPlanRunStatus.RUNNING,
    },
    CareerPlanRunStatus.APPROVED: set(),
    CareerPlanRunStatus.REJECTED: set(),
}


def ensure_run_transition(
    current: CareerPlanRunStatus | str,
    target: CareerPlanRunStatus | str,
) -> CareerPlanRunStatus:
    current_status = CareerPlanRunStatus(current)
    target_status = CareerPlanRunStatus(target)
    if target_status not in _ALLOWED_TRANSITIONS[current_status]:
        raise InvalidCareerPlanTransition(
            f"Career Plan run cannot transition from {current_status.value} to {target_status.value}."
        )
    return target_status
