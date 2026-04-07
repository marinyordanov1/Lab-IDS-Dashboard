"""Normalized data models for alert ingestion."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParsedAlert:
    """Normalized Suricata alert event ready for storage."""

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


@dataclass(frozen=True, slots=True)
class IngestionResult:
    """Summary of a single ingestion run."""

    source_path: str
    total_lines: int
    parsed_alerts: int
    inserted_alerts: int
    duplicate_alerts: int
    skipped_lines: int
    error_lines: int
    mode: str = "full"
    read_offset_start: int = 0
    read_offset_end: int = 0
    file_inode: int = 0
    started_at: str = ""
    completed_at: str = ""
