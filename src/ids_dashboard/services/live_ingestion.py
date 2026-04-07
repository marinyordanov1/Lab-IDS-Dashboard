"""Background polling watcher for incremental Suricata log ingestion."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import threading

from ids_dashboard.core.exceptions import AppError
from ids_dashboard.services.alerts import AlertService


logger = logging.getLogger(__name__)


class LiveIngestionWatcher:
    """Poll a local Suricata eve.json file for newly appended complete lines."""

    def __init__(
        self,
        alert_service: AlertService,
        *,
        poll_interval_seconds: float,
    ) -> None:
        self.alert_service = alert_service
        self.poll_interval_seconds = poll_interval_seconds
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._running = False
        self._last_poll_at: str | None = None
        self._last_error: str | None = None

    def start(self) -> None:
        """Start the watcher thread if it is not already running."""

        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="ids-dashboard-live-ingestion",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout_seconds: float = 5.0) -> None:
        """Signal the watcher thread to stop and wait briefly for shutdown."""

        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout_seconds)

    def snapshot(self) -> dict[str, object]:
        """Return the latest in-memory watcher state."""

        with self._lock:
            return {
                "running": self._running,
                "last_poll_at": self._last_poll_at,
                "last_error": self._last_error,
            }

    def _run(self) -> None:
        with self._lock:
            self._running = True

        try:
            while not self._stop_event.is_set():
                try:
                    self.alert_service.ingest_incremental_file(
                        self.alert_service.settings.suricata_log_path
                    )
                    self._update_snapshot(error_message=None)
                except AppError as exc:
                    logger.warning("Live ingestion watcher poll failed: %s", exc.message)
                    self._update_snapshot(error_message=exc.message)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Unexpected watcher failure", exc_info=exc)
                    self._update_snapshot(error_message=str(exc))

                self._stop_event.wait(self.poll_interval_seconds)
        finally:
            with self._lock:
                self._running = False

    def _update_snapshot(self, *, error_message: str | None) -> None:
        with self._lock:
            self._last_poll_at = datetime.now(timezone.utc).isoformat().replace(
                "+00:00",
                "Z",
            )
            self._last_error = error_message

