"""Suricata alert parsing utilities."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import ipaddress
import json

from ids_dashboard.core.exceptions import IngestionError
from ids_dashboard.ingestion.models import ParsedAlert


REQUIRED_TOP_LEVEL_FIELDS = (
    "timestamp",
    "src_ip",
    "src_port",
    "dest_ip",
    "dest_port",
    "proto",
    "alert",
)
REQUIRED_ALERT_FIELDS = ("severity", "signature_id", "signature", "category")


def normalize_timestamp(timestamp_value: str) -> str:
    """Convert a Suricata timestamp into a canonical UTC string."""

    candidate = timestamp_value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise IngestionError(f"Invalid timestamp: {timestamp_value}") from exc

    if parsed.tzinfo is None:
        raise IngestionError("Timestamp must include timezone information.")

    normalized = parsed.astimezone(timezone.utc)
    return normalized.isoformat().replace("+00:00", "Z")


def _validate_required_fields(event: dict[str, object]) -> None:
    missing = [field for field in REQUIRED_TOP_LEVEL_FIELDS if field not in event]
    if missing:
        raise IngestionError(
            f"Alert event is missing required field(s): {', '.join(sorted(missing))}"
        )

    alert = event.get("alert")
    if not isinstance(alert, dict):
        raise IngestionError("Alert field must be a JSON object.")

    missing_alert_fields = [
        field for field in REQUIRED_ALERT_FIELDS if field not in alert
    ]
    if missing_alert_fields:
        raise IngestionError(
            "Alert metadata is missing required field(s): "
            f"{', '.join(sorted(missing_alert_fields))}"
        )


def _validate_ip_address(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise IngestionError(f"{field_name} must be a string.")

    try:
        return str(ipaddress.ip_address(value))
    except ValueError as exc:
        raise IngestionError(f"{field_name} is not a valid IP address: {value}") from exc


def _validate_port(value: object, field_name: str) -> int:
    if isinstance(value, bool):
        raise IngestionError(f"{field_name} must be an integer.")

    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise IngestionError(f"{field_name} must be an integer.") from exc

    if not 0 <= port <= 65535:
        raise IngestionError(f"{field_name} must be between 0 and 65535.")
    return port


def _validate_int(value: object, field_name: str) -> int:
    if isinstance(value, bool):
        raise IngestionError(f"{field_name} must be an integer.")

    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise IngestionError(f"{field_name} must be an integer.") from exc


def _validate_severity(value: object) -> int:
    severity = _validate_int(value, "severity")
    if not 1 <= severity <= 5:
        raise IngestionError("severity must be between 1 and 5.")
    return severity


def _build_fingerprint(normalized_alert: dict[str, object]) -> str:
    payload = json.dumps(
        normalized_alert,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def parse_suricata_line(line: str) -> ParsedAlert | None:
    """Parse a single JSON line from Suricata `eve.json`.

    Returns `None` for blank lines or non-alert events.
    """

    stripped = line.strip()
    if not stripped:
        return None

    try:
        event = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise IngestionError("Malformed JSON line encountered during ingestion.") from exc

    if not isinstance(event, dict):
        raise IngestionError("Each Suricata line must decode to a JSON object.")

    if event.get("event_type") != "alert":
        return None

    _validate_required_fields(event)
    alert = event["alert"]
    assert isinstance(alert, dict)

    normalized_payload = {
        "timestamp": normalize_timestamp(str(event["timestamp"])),
        "src_ip": _validate_ip_address(event["src_ip"], "src_ip"),
        "src_port": _validate_port(event["src_port"], "src_port"),
        "dest_ip": _validate_ip_address(event["dest_ip"], "dest_ip"),
        "dest_port": _validate_port(event["dest_port"], "dest_port"),
        "protocol": str(event["proto"]).upper(),
        "severity": _validate_severity(alert["severity"]),
        "signature_id": _validate_int(alert["signature_id"], "signature_id"),
        "signature": str(alert["signature"]).strip(),
        "category": str(alert["category"]).strip(),
    }

    if not normalized_payload["protocol"]:
        raise IngestionError("proto cannot be empty.")
    if not normalized_payload["signature"]:
        raise IngestionError("signature cannot be empty.")
    if not normalized_payload["category"]:
        raise IngestionError("category cannot be empty.")

    fingerprint = _build_fingerprint(normalized_payload)
    raw_event = json.dumps(event, sort_keys=True, separators=(",", ":"))

    return ParsedAlert(
        timestamp=normalized_payload["timestamp"],
        src_ip=normalized_payload["src_ip"],
        src_port=normalized_payload["src_port"],
        dest_ip=normalized_payload["dest_ip"],
        dest_port=normalized_payload["dest_port"],
        protocol=normalized_payload["protocol"],
        severity=normalized_payload["severity"],
        signature_id=normalized_payload["signature_id"],
        signature=normalized_payload["signature"],
        category=normalized_payload["category"],
        event_fingerprint=fingerprint,
        raw_event=raw_event,
    )
