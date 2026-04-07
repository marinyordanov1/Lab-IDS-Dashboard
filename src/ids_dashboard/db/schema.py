"""SQLite schema definitions."""

from __future__ import annotations


SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        src_ip TEXT NOT NULL,
        src_port INTEGER NOT NULL CHECK (src_port BETWEEN 0 AND 65535),
        dest_ip TEXT NOT NULL,
        dest_port INTEGER NOT NULL CHECK (dest_port BETWEEN 0 AND 65535),
        protocol TEXT NOT NULL,
        severity INTEGER NOT NULL CHECK (severity BETWEEN 1 AND 5),
        signature_id INTEGER NOT NULL,
        signature TEXT NOT NULL,
        category TEXT NOT NULL,
        event_fingerprint TEXT NOT NULL UNIQUE,
        raw_event TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp DESC)",
    "CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity)",
    "CREATE INDEX IF NOT EXISTS idx_alerts_signature_id ON alerts(signature_id)",
    """
    CREATE TABLE IF NOT EXISTS ingestion_state (
        source_path TEXT PRIMARY KEY,
        file_inode INTEGER NOT NULL DEFAULT 0,
        file_offset INTEGER NOT NULL DEFAULT 0,
        last_line_number INTEGER NOT NULL DEFAULT 0,
        last_poll_at TEXT,
        last_status TEXT NOT NULL DEFAULT 'idle',
        last_error_message TEXT,
        last_run_mode TEXT,
        last_run_started_at TEXT,
        last_run_completed_at TEXT,
        last_total_lines INTEGER NOT NULL DEFAULT 0,
        last_parsed_alerts INTEGER NOT NULL DEFAULT 0,
        last_inserted_alerts INTEGER NOT NULL DEFAULT 0,
        last_duplicate_alerts INTEGER NOT NULL DEFAULT 0,
        last_skipped_lines INTEGER NOT NULL DEFAULT 0,
        last_error_lines INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ingestion_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_path TEXT NOT NULL,
        mode TEXT NOT NULL,
        status TEXT NOT NULL,
        total_lines INTEGER NOT NULL DEFAULT 0,
        parsed_alerts INTEGER NOT NULL DEFAULT 0,
        inserted_alerts INTEGER NOT NULL DEFAULT 0,
        duplicate_alerts INTEGER NOT NULL DEFAULT 0,
        skipped_lines INTEGER NOT NULL DEFAULT 0,
        error_lines INTEGER NOT NULL DEFAULT 0,
        read_offset_start INTEGER NOT NULL DEFAULT 0,
        read_offset_end INTEGER NOT NULL DEFAULT 0,
        file_inode INTEGER NOT NULL DEFAULT 0,
        started_at TEXT,
        completed_at TEXT,
        error_message TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_ingestion_runs_source_completed
    ON ingestion_runs(source_path, completed_at DESC)
    """,
)
