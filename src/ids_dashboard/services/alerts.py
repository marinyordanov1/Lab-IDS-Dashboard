"""Service layer for alert ingestion and reporting."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path

from ids_dashboard.core.config import PROJECT_ROOT, Settings
from ids_dashboard.core.exceptions import IngestionError, ResourceNotFoundError
from ids_dashboard.db.database import initialize_database, open_connection
from ids_dashboard.db.repository import AlertRepository
from ids_dashboard.ingestion.models import IngestionResult, ParsedAlert
from ids_dashboard.ingestion.parser import parse_suricata_line


logger = logging.getLogger(__name__)


class AlertService:
    """Coordinate alert ingestion, storage, and reporting."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def initialize_database(self) -> None:
        """Ensure the SQLite schema exists."""

        initialize_database(self.settings)

    def ingest_sample_file(self) -> IngestionResult:
        """Ingest the configured bundled sample file."""

        return self.ingest_file(self.settings.suricata_log_path)

    def ingest_file(
        self,
        path: str | Path,
        *,
        incremental: bool = False,
    ) -> IngestionResult:
        """Parse and persist alerts from a Suricata eve.json file."""

        source_path = self._resolve_path(path)
        if not source_path.exists():
            raise ResourceNotFoundError(f"Alert source file does not exist: {source_path}")

        if incremental:
            return self._ingest_incremental_file(source_path)
        return self._ingest_full_file(source_path)

    def ingest_incremental_file(self, path: str | Path) -> IngestionResult:
        """Ingest only newly appended, complete lines from a Suricata eve.json file."""

        return self.ingest_file(path, incremental=True)

    def list_alerts(
        self,
        *,
        limit: int = 50,
        severity: int | None = None,
        signature: str | None = None,
    ) -> list[dict[str, object]]:
        """Return recent alerts with optional filtering."""

        self.initialize_database()
        with open_connection(self.settings) as connection:
            repository = AlertRepository(connection)
            return repository.list_alerts(
                limit=max(1, min(limit, 500)),
                severity=severity,
                signature=signature,
            )

    def get_summary(self) -> dict[str, object]:
        """Return aggregate alert statistics."""

        self.initialize_database()
        with open_connection(self.settings) as connection:
            repository = AlertRepository(connection)
            return repository.get_summary()

    def list_ingestion_runs(
        self,
        *,
        limit: int = 10,
        path: str | Path | None = None,
    ) -> list[dict[str, object]]:
        """Return recent ingestion runs for the configured or provided source."""

        source_path = self._resolve_path(path or self.settings.suricata_log_path)
        self.initialize_database()
        with open_connection(self.settings) as connection:
            repository = AlertRepository(connection)
            return repository.list_ingestion_runs(
                source_path=str(source_path),
                limit=max(1, min(limit, 50)),
            )

    def get_ingestion_status(
        self,
        *,
        watcher_snapshot: dict[str, object] | None = None,
        path: str | Path | None = None,
    ) -> dict[str, object]:
        """Return incremental ingestion status for the configured or provided source."""

        source_path = self._resolve_path(path or self.settings.suricata_log_path)
        self.initialize_database()
        with open_connection(self.settings) as connection:
            repository = AlertRepository(connection)
            state = repository.get_ingestion_state(source_path=str(source_path)) or {}

        file_exists = source_path.exists()
        file_stat = source_path.stat() if file_exists else None
        return {
            "source_path": str(source_path),
            "file_exists": file_exists,
            "watcher_enabled": self.settings.enable_live_ingestion,
            "watcher_running": bool(watcher_snapshot.get("running"))
            if watcher_snapshot
            else False,
            "poll_interval_seconds": self.settings.live_ingestion_poll_interval_seconds,
            "dashboard_auto_refresh_seconds": self.settings.dashboard_auto_refresh_seconds,
            "current_file_inode": int(file_stat.st_ino) if file_stat else None,
            "current_file_size": int(file_stat.st_size) if file_stat else 0,
            "file_offset": int(state.get("file_offset", 0)),
            "last_line_number": int(state.get("last_line_number", 0)),
            "last_poll_at": state.get("last_poll_at"),
            "last_status": state.get("last_status", "idle"),
            "last_error_message": state.get("last_error_message"),
            "last_run_mode": state.get("last_run_mode"),
            "last_run_started_at": state.get("last_run_started_at"),
            "last_run_completed_at": state.get("last_run_completed_at"),
            "last_total_lines": int(state.get("last_total_lines", 0)),
            "last_parsed_alerts": int(state.get("last_parsed_alerts", 0)),
            "last_inserted_alerts": int(state.get("last_inserted_alerts", 0)),
            "last_duplicate_alerts": int(state.get("last_duplicate_alerts", 0)),
            "last_skipped_lines": int(state.get("last_skipped_lines", 0)),
            "last_error_lines": int(state.get("last_error_lines", 0)),
            "total_runs": int(state.get("total_runs", 0)),
            "watcher_last_poll_at": watcher_snapshot.get("last_poll_at")
            if watcher_snapshot
            else None,
            "watcher_last_error": watcher_snapshot.get("last_error")
            if watcher_snapshot
            else None,
        }

    def _ingest_full_file(self, source_path: Path) -> IngestionResult:
        self.initialize_database()

        started_at = self._utc_now_iso()
        file_stat = source_path.stat()
        raw_bytes = source_path.read_bytes()
        parsed_alerts, total_lines, skipped_lines, error_lines = self._parse_bytes_block(
            raw_bytes,
            source_path=source_path,
            starting_line_number=0,
        )

        with open_connection(self.settings) as connection:
            repository = AlertRepository(connection)
            inserted_alerts = repository.insert_alerts(parsed_alerts)
            result = IngestionResult(
                source_path=str(source_path),
                total_lines=total_lines,
                parsed_alerts=len(parsed_alerts),
                inserted_alerts=inserted_alerts,
                duplicate_alerts=len(parsed_alerts) - inserted_alerts,
                skipped_lines=skipped_lines,
                error_lines=error_lines,
                mode="full",
                read_offset_start=0,
                read_offset_end=len(raw_bytes),
                file_inode=int(file_stat.st_ino),
                started_at=started_at,
                completed_at=self._utc_now_iso(),
            )
            status = self._status_for_result(result)
            repository.insert_ingestion_run(result=result, status=status)
            repository.upsert_ingestion_state(
                source_path=str(source_path),
                file_inode=int(file_stat.st_ino),
                file_offset=len(raw_bytes),
                last_line_number=total_lines,
                last_poll_at=result.completed_at,
                status=status,
                result=result,
            )

        self._log_ingestion_result(result)
        return result

    def _ingest_incremental_file(self, source_path: Path) -> IngestionResult:
        self.initialize_database()

        started_at = self._utc_now_iso()
        file_stat = source_path.stat()
        file_inode = int(file_stat.st_ino)
        file_size = int(file_stat.st_size)

        with open_connection(self.settings) as connection:
            repository = AlertRepository(connection)
            prior_state = repository.get_ingestion_state(source_path=str(source_path))
            start_offset, start_line_number = self._determine_incremental_cursor(
                prior_state,
                file_inode=file_inode,
                file_size=file_size,
            )

            with source_path.open("rb") as handle:
                handle.seek(start_offset)
                unread_bytes = handle.read()

            complete_line_bytes = self._extract_complete_line_bytes(unread_bytes)
            if not complete_line_bytes:
                completed_at = self._utc_now_iso()
                result = IngestionResult(
                    source_path=str(source_path),
                    total_lines=0,
                    parsed_alerts=0,
                    inserted_alerts=0,
                    duplicate_alerts=0,
                    skipped_lines=0,
                    error_lines=0,
                    mode="incremental",
                    read_offset_start=start_offset,
                    read_offset_end=start_offset,
                    file_inode=file_inode,
                    started_at=started_at,
                    completed_at=completed_at,
                )
                repository.upsert_ingestion_state(
                    source_path=str(source_path),
                    file_inode=file_inode,
                    file_offset=start_offset,
                    last_line_number=start_line_number,
                    last_poll_at=completed_at,
                    status="no_new_data",
                    result=None,
                )
                return result

            parsed_alerts, total_lines, skipped_lines, error_lines = self._parse_bytes_block(
                complete_line_bytes,
                source_path=source_path,
                starting_line_number=start_line_number,
            )
            inserted_alerts = repository.insert_alerts(parsed_alerts)
            end_offset = start_offset + len(complete_line_bytes)
            result = IngestionResult(
                source_path=str(source_path),
                total_lines=total_lines,
                parsed_alerts=len(parsed_alerts),
                inserted_alerts=inserted_alerts,
                duplicate_alerts=len(parsed_alerts) - inserted_alerts,
                skipped_lines=skipped_lines,
                error_lines=error_lines,
                mode="incremental",
                read_offset_start=start_offset,
                read_offset_end=end_offset,
                file_inode=file_inode,
                started_at=started_at,
                completed_at=self._utc_now_iso(),
            )
            status = self._status_for_result(result)
            repository.insert_ingestion_run(result=result, status=status)
            repository.upsert_ingestion_state(
                source_path=str(source_path),
                file_inode=file_inode,
                file_offset=end_offset,
                last_line_number=start_line_number + total_lines,
                last_poll_at=result.completed_at,
                status=status,
                result=result,
            )

        self._log_ingestion_result(result)
        return result

    def _parse_bytes_block(
        self,
        raw_bytes: bytes,
        *,
        source_path: Path,
        starting_line_number: int,
    ) -> tuple[list[ParsedAlert], int, int, int]:
        parsed_alerts: list[ParsedAlert] = []
        total_lines = 0
        skipped_lines = 0
        error_lines = 0

        for relative_line_number, line_bytes in enumerate(raw_bytes.splitlines(), start=1):
            total_lines += 1
            absolute_line_number = starting_line_number + relative_line_number
            try:
                line = line_bytes.decode("utf-8")
            except UnicodeDecodeError as exc:
                error_lines += 1
                logger.warning(
                    "Skipping undecodable alert line %s from %s: %s",
                    absolute_line_number,
                    source_path,
                    exc,
                )
                continue

            try:
                parsed = parse_suricata_line(line)
            except IngestionError as exc:
                error_lines += 1
                logger.warning(
                    "Skipping invalid alert line %s from %s: %s",
                    absolute_line_number,
                    source_path,
                    exc,
                )
                continue

            if parsed is None:
                skipped_lines += 1
                continue

            parsed_alerts.append(parsed)

        return parsed_alerts, total_lines, skipped_lines, error_lines

    @staticmethod
    def _extract_complete_line_bytes(raw_bytes: bytes) -> bytes:
        if not raw_bytes:
            return b""

        last_newline_index = raw_bytes.rfind(b"\n")
        if last_newline_index == -1:
            return b""
        return raw_bytes[: last_newline_index + 1]

    @staticmethod
    def _determine_incremental_cursor(
        prior_state: dict[str, object] | None,
        *,
        file_inode: int,
        file_size: int,
    ) -> tuple[int, int]:
        if not prior_state:
            return 0, 0

        prior_inode = int(prior_state.get("file_inode", 0))
        prior_offset = int(prior_state.get("file_offset", 0))
        prior_line_number = int(prior_state.get("last_line_number", 0))
        if prior_inode != file_inode or file_size < prior_offset:
            return 0, 0
        return prior_offset, prior_line_number

    @staticmethod
    def _status_for_result(result: IngestionResult) -> str:
        if result.total_lines == 0:
            return "no_new_data"
        if result.error_lines > 0:
            return "completed_with_errors"
        return "success"

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _log_ingestion_result(result: IngestionResult) -> None:
        logger.info(
            "%s ingestion processed %s line(s) from %s (%s inserted, %s duplicates, %s skipped, %s errors)",
            result.mode,
            result.total_lines,
            result.source_path,
            result.inserted_alerts,
            result.duplicate_alerts,
            result.skipped_lines,
            result.error_lines,
        )

    @staticmethod
    def _resolve_path(path: str | Path) -> Path:
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate
        return candidate
