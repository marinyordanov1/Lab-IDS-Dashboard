from __future__ import annotations

import json

import pytest

from ids_dashboard.core.exceptions import IngestionError
from ids_dashboard.ingestion.parser import normalize_timestamp, parse_suricata_line


def test_parse_valid_alert_line_normalizes_fields() -> None:
    line = json.dumps(
        {
            "timestamp": "2026-04-07T11:15:30+03:00",
            "event_type": "alert",
            "src_ip": "10.10.0.5",
            "src_port": 51514,
            "dest_ip": "10.10.0.10",
            "dest_port": 80,
            "proto": "tcp",
            "alert": {
                "severity": 2,
                "signature_id": 1000001,
                "signature": "AUTHORIZED LAB Demo HTTP marker detected",
                "category": "Authorized Lab Monitoring",
            },
        }
    )

    parsed = parse_suricata_line(line)

    assert parsed is not None
    assert parsed.timestamp == "2026-04-07T08:15:30Z"
    assert parsed.protocol == "TCP"
    assert parsed.src_ip == "10.10.0.5"
    assert parsed.signature_id == 1000001
    assert len(parsed.event_fingerprint) == 64


def test_parse_non_alert_event_returns_none() -> None:
    line = json.dumps(
        {
            "timestamp": "2026-04-07T08:16:01+00:00",
            "event_type": "dns",
            "src_ip": "10.10.0.6",
            "src_port": 53022,
            "dest_ip": "10.10.0.20",
            "dest_port": 53,
            "proto": "udp",
            "dns": {"rrname": "training.invalid"},
        }
    )

    assert parse_suricata_line(line) is None


def test_parse_invalid_json_raises_ingestion_error() -> None:
    with pytest.raises(IngestionError, match="Malformed JSON"):
        parse_suricata_line("{not-json}")


def test_parse_alert_missing_required_field_raises_ingestion_error() -> None:
    line = json.dumps(
        {
            "timestamp": "2026-04-07T08:15:30+00:00",
            "event_type": "alert",
            "src_ip": "10.10.0.5",
            "src_port": 51514,
            "dest_ip": "10.10.0.10",
            "proto": "tcp",
            "alert": {
                "severity": 2,
                "signature_id": 1000001,
                "signature": "AUTHORIZED LAB Demo HTTP marker detected",
                "category": "Authorized Lab Monitoring",
            },
        }
    )

    with pytest.raises(IngestionError, match="missing required field"):
        parse_suricata_line(line)


def test_normalize_timestamp_converts_to_utc() -> None:
    assert normalize_timestamp("2026-04-07T11:15:30+03:00") == "2026-04-07T08:15:30Z"

