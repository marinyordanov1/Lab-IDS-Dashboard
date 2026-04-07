"""Pydantic response schemas for API endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class AlertOut(BaseModel):
    """Serialized alert response."""

    timestamp: str
    src_ip: str
    src_port: int
    dest_ip: str
    dest_port: int
    protocol: str
    severity: int
    signature_id: int
    signature: str
    category: str
    event_fingerprint: str
    raw_event: str


class SeverityCountOut(BaseModel):
    """Aggregated alert count by severity."""

    severity: int
    count: int


class SignatureCountOut(BaseModel):
    """Aggregated alert count by signature."""

    signature_id: int
    signature: str
    count: int


class FlowCountOut(BaseModel):
    """Aggregated alert count by source and destination."""

    src_ip: str
    dest_ip: str
    count: int


class SummaryOut(BaseModel):
    """Summary response model for dashboard aggregates."""

    total_alerts: int
    latest_timestamp: str | None
    alerts_by_severity: list[SeverityCountOut]
    top_signatures: list[SignatureCountOut]
    top_flows: list[FlowCountOut]


class IngestionStatusOut(BaseModel):
    """Current incremental ingestion status."""

    source_path: str
    file_exists: bool
    watcher_enabled: bool
    watcher_running: bool
    poll_interval_seconds: float
    dashboard_auto_refresh_seconds: int
    current_file_inode: int | None
    current_file_size: int
    file_offset: int
    last_line_number: int
    last_poll_at: str | None
    last_status: str
    last_error_message: str | None
    last_run_mode: str | None
    last_run_started_at: str | None
    last_run_completed_at: str | None
    last_total_lines: int
    last_parsed_alerts: int
    last_inserted_alerts: int
    last_duplicate_alerts: int
    last_skipped_lines: int
    last_error_lines: int
    total_runs: int
    watcher_last_poll_at: str | None
    watcher_last_error: str | None


class IngestionRunOut(BaseModel):
    """Historical ingestion run record."""

    source_path: str
    mode: str
    status: str
    total_lines: int
    parsed_alerts: int
    inserted_alerts: int
    duplicate_alerts: int
    skipped_lines: int
    error_lines: int
    read_offset_start: int
    read_offset_end: int
    file_inode: int
    started_at: str | None
    completed_at: str | None
    error_message: str | None
