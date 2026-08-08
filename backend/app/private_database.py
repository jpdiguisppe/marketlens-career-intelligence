from collections.abc import Generator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.auth import AuthenticatedUser, get_current_user
from app.database import bind_authenticated_user, clear_authenticated_user, get_db
from app.security import enforce_private_rate_limit


def get_user_db(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Generator[Session, None, None]:
    """Yield a database session bound to the authenticated user.

    FastAPI caches ``get_current_user`` within the request, so private routes can
    still receive the same ``AuthenticatedUser`` separately while this dependency
    installs the database RLS context before any user-owned query executes.
    """

    enforce_private_rate_limit(request, current_user.user_id)
    bind_authenticated_user(db, current_user.user_id)
    try:
        yield db
    finally:
        clear_authenticated_user(db)
