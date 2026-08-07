import pytest
from sqlalchemy.orm import Session

from app.database import (
    MAX_DATABASE_USER_ID_LENGTH,
    RLS_SESSION_USER_KEY,
    bind_authenticated_user,
    clear_authenticated_user,
)


def test_bind_and_clear_authenticated_database_user_context() -> None:
    session = Session()
    try:
        bind_authenticated_user(session, "  clerk-user-123  ")
        assert session.info[RLS_SESSION_USER_KEY] == "clerk-user-123"

        clear_authenticated_user(session)
        assert RLS_SESSION_USER_KEY not in session.info
    finally:
        session.close()


@pytest.mark.parametrize("user_id", ["", "   ", "x" * (MAX_DATABASE_USER_ID_LENGTH + 1)])
def test_invalid_database_user_context_fails_closed(user_id: str) -> None:
    session = Session()
    try:
        with pytest.raises(RuntimeError, match="Authenticated database user context is invalid"):
            bind_authenticated_user(session, user_id)
        assert RLS_SESSION_USER_KEY not in session.info
    finally:
        session.close()
