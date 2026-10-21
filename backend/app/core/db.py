from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


_SQLITE_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "jobs": [
        ("imported_manually", "BOOLEAN DEFAULT 0"),
        ("link_only", "BOOLEAN DEFAULT 0"),
    ],
    "preferences": [
        ("freshness_days", "INTEGER DEFAULT 2"),
        ("auto_submit_enabled", "BOOLEAN DEFAULT 0"),
        ("auto_submit_max_per_run", "INTEGER DEFAULT 5"),
        ("default_cv_source", "VARCHAR(20) DEFAULT 'tailored'"),
    ],
    "applications": [
        ("cv_source", "VARCHAR(20) DEFAULT 'tailored'"),
        ("cv_file_name", "VARCHAR(300) DEFAULT ''"),
        ("portal_mode", "VARCHAR(30) DEFAULT 'manual_only'"),
        ("application_url", "VARCHAR(700) DEFAULT ''"),
    ],
}


def _migrate_sqlite_columns() -> None:
    """Add new columns to existing SQLite databases without a migration tool.

    This is a personal, local-first app; keeping a tiny forward-only migration
    here avoids making users delete their database when a new feature lands.
    """
    if not settings.database_url.startswith("sqlite"):
        return
    with engine.begin() as connection:
        for table, columns in _SQLITE_COLUMNS.items():
            existing = {
                row[1]
                for row in connection.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
            }
            for name, ddl in columns:
                if name not in existing:
                    connection.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def init_db() -> None:
    from app import models  # noqa: F401  (register models)

    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_columns()
