"""Repository helpers for alert persistence and reporting."""

from __future__ import annotations

import sqlite3
from typing import Any

from ids_dashboard.ingestion.models import IngestionResult, ParsedAlert


class AlertRepository:
    """Encapsulate SQLite operations for alert records."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def insert_alerts(self, alerts: list[ParsedAlert]) -> int:
        """Insert alerts with deduplication based on fingerprint."""

        if not alerts:
            return 0

        before_changes = self.connection.total_changes
        self.connection.executemany(
            """
            INSERT OR IGNORE INTO alerts (
                timestamp,
                src_ip,
                src_port,
                dest_ip,
                dest_port,
                protocol,
                severity,
                signature_id,
                signature,
                category,
                event_fingerprint,
                raw_event
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    alert.timestamp,
                    alert.src_ip,
                    alert.src_port,
                    alert.dest_ip,
                    alert.dest_port,
                    alert.protocol,
                    alert.severity,
                    alert.signature_id,
                    alert.signature,
                    alert.category,
                    alert.event_fingerprint,
                    alert.raw_event,
                )
                for alert in alerts
            ],
        )
        return self.connection.total_changes - before_changes

    def list_alerts(
        self,
        *,
        limit: int,
        severity: int | None = None,
        signature: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return alerts ordered by newest first."""

        query = """
            SELECT
                timestamp,
                src_ip,
                src_port,
                dest_ip,
                dest_port,
                protocol,
                severity,
                signature_id,
                signature,
                category,
                event_fingerprint,
                raw_event
            FROM alerts
        """
        conditions: list[str] = []
        parameters: list[Any] = []

        if severity is not None:
            conditions.append("severity = ?")
            parameters.append(severity)

        if signature:
            conditions.append("signature LIKE ?")
            parameters.append(f"%{signature.strip()}%")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY timestamp DESC LIMIT ?"
        parameters.append(limit)

        rows = self.connection.execute(query, parameters).fetchall()
        return [dict(row) for row in rows]

    def get_summary(self) -> dict[str, Any]:
        """Return aggregate metrics for the dashboard and API."""

        overview = self.connection.execute(
            """
            SELECT COUNT(*) AS total_alerts, MAX(timestamp) AS latest_timestamp
            FROM alerts
            """
        ).fetchone()

        severity_rows = self.connection.execute(
            """
            SELECT severity, COUNT(*) AS count
            FROM alerts
            GROUP BY severity
            ORDER BY severity ASC
            """
        ).fetchall()

        signature_rows = self.connection.execute(
            """
            SELECT signature_id, signature, COUNT(*) AS count
            FROM alerts
            GROUP BY signature_id, signature
            ORDER BY count DESC, signature ASC
            LIMIT 5
            """
        ).fetchall()

        flow_rows = self.connection.execute(
            """
            SELECT src_ip, dest_ip, COUNT(*) AS count
            FROM alerts
            GROUP BY src_ip, dest_ip
            ORDER BY count DESC, src_ip ASC, dest_ip ASC
            LIMIT 5
            """
        ).fetchall()

        return {
            "total_alerts": int(overview["total_alerts"]) if overview else 0,
            "latest_timestamp": overview["latest_timestamp"] if overview else None,
            "alerts_by_severity": [dict(row) for row in severity_rows],
            "top_signatures": [dict(row) for row in signature_rows],
            "top_flows": [dict(row) for row in flow_rows],
        }

    def get_ingestion_state(self, *, source_path: str) -> dict[str, Any] | None:
        """Return the stored incremental ingestion state for a source path."""

        row = self.connection.execute(
            """
            SELECT
                ingestion_state.*,
                (
                    SELECT COUNT(*)
                    FROM ingestion_runs
                    WHERE ingestion_runs.source_path = ingestion_state.source_path
                ) AS total_runs
            FROM ingestion_state
            WHERE source_path = ?
            """,
            (source_path,),
        ).fetchone()
        return dict(row) if row else None

    def upsert_ingestion_state(
        self,
        *,
        source_path: str,
        file_inode: int,
        file_offset: int,
        last_line_number: int,
        last_poll_at: str,
        status: str,
        error_message: str | None = None,
        result: IngestionResult | None = None,
    ) -> None:
        """Persist the last-known ingestion cursor and summary state."""

        existing_state = self.get_ingestion_state(source_path=source_path) or {}
        run_mode = result.mode if result else existing_state.get("last_run_mode")
        run_started_at = (
            result.started_at if result else existing_state.get("last_run_started_at")
        )
        run_completed_at = (
            result.completed_at if result else existing_state.get("last_run_completed_at")
        )
        total_lines = (
            result.total_lines
            if result
            else int(existing_state.get("last_total_lines", 0))
        )
        parsed_alerts = (
            result.parsed_alerts
            if result
            else int(existing_state.get("last_parsed_alerts", 0))
        )
        inserted_alerts = (
            result.inserted_alerts
            if result
            else int(existing_state.get("last_inserted_alerts", 0))
        )
        duplicate_alerts = (
            result.duplicate_alerts
            if result
            else int(existing_state.get("last_duplicate_alerts", 0))
        )
        skipped_lines = (
            result.skipped_lines
            if result
            else int(existing_state.get("last_skipped_lines", 0))
        )
        error_lines = (
            result.error_lines
            if result
            else int(existing_state.get("last_error_lines", 0))
        )

        self.connection.execute(
            """
            INSERT INTO ingestion_state (
                source_path,
                file_inode,
                file_offset,
                last_line_number,
                last_poll_at,
                last_status,
                last_error_message,
                last_run_mode,
                last_run_started_at,
                last_run_completed_at,
                last_total_lines,
                last_parsed_alerts,
                last_inserted_alerts,
                last_duplicate_alerts,
                last_skipped_lines,
                last_error_lines,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(source_path) DO UPDATE SET
                file_inode = excluded.file_inode,
                file_offset = excluded.file_offset,
                last_line_number = excluded.last_line_number,
                last_poll_at = excluded.last_poll_at,
                last_status = excluded.last_status,
                last_error_message = excluded.last_error_message,
                last_run_mode = COALESCE(excluded.last_run_mode, ingestion_state.last_run_mode),
                last_run_started_at = COALESCE(
                    excluded.last_run_started_at,
                    ingestion_state.last_run_started_at
                ),
                last_run_completed_at = COALESCE(
                    excluded.last_run_completed_at,
                    ingestion_state.last_run_completed_at
                ),
                last_total_lines = COALESCE(
                    excluded.last_total_lines,
                    ingestion_state.last_total_lines
                ),
                last_parsed_alerts = COALESCE(
                    excluded.last_parsed_alerts,
                    ingestion_state.last_parsed_alerts
                ),
                last_inserted_alerts = COALESCE(
                    excluded.last_inserted_alerts,
                    ingestion_state.last_inserted_alerts
                ),
                last_duplicate_alerts = COALESCE(
                    excluded.last_duplicate_alerts,
                    ingestion_state.last_duplicate_alerts
                ),
                last_skipped_lines = COALESCE(
                    excluded.last_skipped_lines,
                    ingestion_state.last_skipped_lines
                ),
                last_error_lines = COALESCE(
                    excluded.last_error_lines,
                    ingestion_state.last_error_lines
                ),
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                source_path,
                file_inode,
                file_offset,
                last_line_number,
                last_poll_at,
                status,
                error_message,
                run_mode,
                run_started_at,
                run_completed_at,
                total_lines,
                parsed_alerts,
                inserted_alerts,
                duplicate_alerts,
                skipped_lines,
                error_lines,
            ),
        )

    def insert_ingestion_run(
        self,
        *,
        result: IngestionResult,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """Store a historical ingestion run record."""

        self.connection.execute(
            """
            INSERT INTO ingestion_runs (
                source_path,
                mode,
                status,
                total_lines,
                parsed_alerts,
                inserted_alerts,
                duplicate_alerts,
                skipped_lines,
                error_lines,
                read_offset_start,
                read_offset_end,
                file_inode,
                started_at,
                completed_at,
                error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.source_path,
                result.mode,
                status,
                result.total_lines,
                result.parsed_alerts,
                result.inserted_alerts,
                result.duplicate_alerts,
                result.skipped_lines,
                result.error_lines,
                result.read_offset_start,
                result.read_offset_end,
                result.file_inode,
                result.started_at,
                result.completed_at,
                error_message,
            ),
        )

    def list_ingestion_runs(
        self,
        *,
        source_path: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Return recent ingestion run history for a source path."""

        rows = self.connection.execute(
            """
            SELECT
                source_path,
                mode,
                status,
                total_lines,
                parsed_alerts,
                inserted_alerts,
                duplicate_alerts,
                skipped_lines,
                error_lines,
                read_offset_start,
                read_offset_end,
                file_inode,
                started_at,
                completed_at,
                error_message
            FROM ingestion_runs
            WHERE source_path = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (source_path, limit),
        ).fetchall()
        return [dict(row) for row in rows]
