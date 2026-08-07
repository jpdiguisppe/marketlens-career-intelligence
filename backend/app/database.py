import os

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./marketlens.db")
RLS_SESSION_USER_KEY = "marketlens_user_id"
RLS_POSTGRES_SETTING = "app.current_user_id"
MAX_DATABASE_USER_ID_LENGTH = 255

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


@event.listens_for(Session, "after_begin")
def _apply_postgres_rls_user_context(
    session: Session,
    _transaction: object,
    connection: object,
) -> None:
    """Bind the authenticated user to each PostgreSQL transaction.

    The value lives only in ``Session.info`` between transactions. PostgreSQL
    receives it through ``set_config(..., true)``, which makes the database
    setting transaction-local. This prevents pooled connections from carrying a
    user identity into another request while still reapplying the identity after
    application code commits and starts a new transaction for refresh/readback.
    """

    dialect = getattr(connection, "dialect", None)
    if getattr(dialect, "name", None) != "postgresql":
        return

    user_id = session.info.get(RLS_SESSION_USER_KEY)
    if not isinstance(user_id, str) or not user_id:
        return

    connection.execute(
        text("SELECT set_config(:setting_name, :user_id, true)"),
        {
            "setting_name": RLS_POSTGRES_SETTING,
            "user_id": user_id,
        },
    )


def bind_authenticated_user(db: Session, user_id: str) -> None:
    """Attach a validated authenticated user ID to a SQLAlchemy session."""

    normalized_user_id = user_id.strip() if isinstance(user_id, str) else ""
    if not normalized_user_id or len(normalized_user_id) > MAX_DATABASE_USER_ID_LENGTH:
        raise RuntimeError("Authenticated database user context is invalid.")

    db.info[RLS_SESSION_USER_KEY] = normalized_user_id


def clear_authenticated_user(db: Session) -> None:
    """Remove request identity from the SQLAlchemy session before it is reused."""

    db.info.pop(RLS_SESSION_USER_KEY, None)


def initialize_database_schema() -> None:
    """Create local SQLite tables only.

    PostgreSQL production schema changes are intentionally migration-owned so a
    restricted runtime role never needs CREATE/ALTER privileges.
    """

    if engine.dialect.name == "sqlite":
        Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
