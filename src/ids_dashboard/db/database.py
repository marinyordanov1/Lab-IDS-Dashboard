"""SQLite connection helpers."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterator

from ids_dashboard.core.config import Settings
from ids_dashboard.db.schema import SCHEMA_STATEMENTS


def _ensure_parent_directory(database_target: str) -> None:
    if database_target == ":memory:":
        return
    Path(database_target).parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def open_connection(settings: Settings) -> Iterator[sqlite3.Connection]:
    """Yield a configured SQLite connection."""

    database_target = settings.database_target
    _ensure_parent_directory(database_target)
    connection = sqlite3.connect(database_target, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def initialize_database(settings: Settings) -> None:
    """Create the SQLite schema if it does not exist."""

    with open_connection(settings) as connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)

