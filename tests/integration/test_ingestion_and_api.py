from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from ids_dashboard.core.config import Settings
from ids_dashboard.services.alerts import AlertService


def test_ingest_file_persists_alerts_and_skips_duplicates(
    alert_service: AlertService,
    sample_alert_file: Path,
) -> None:
    result = alert_service.ingest_file(sample_alert_file)

    assert result.total_lines == 4
    assert result.parsed_alerts == 3
    assert result.inserted_alerts == 2
    assert result.duplicate_alerts == 1
    assert result.skipped_lines == 1
    assert result.error_lines == 0

    stored_alerts = alert_service.list_alerts(limit=10)
    assert len(stored_alerts) == 2
    assert stored_alerts[0]["severity"] == 1


def test_incremental_ingest_only_reads_new_complete_lines(
    alert_service: AlertService,
    sample_alert_file: Path,
) -> None:
    first_result = alert_service.ingest_incremental_file(sample_alert_file)

    assert first_result.total_lines == 4
    assert first_result.inserted_alerts == 2
    assert first_result.duplicate_alerts == 1

    appended_alert = json.dumps(
        {
            "timestamp": "2026-04-07T08:18:01+00:00",
            "event_type": "alert",
            "src_ip": "10.1.0.8",
            "src_port": 55200,
            "dest_ip": "10.1.0.40",
            "dest_port": 443,
            "proto": "TCP",
            "alert": {
                "severity": 2,
                "signature_id": 1000004,
                "signature": "AUTHORIZED LAB Demo TLS policy deviation",
                "category": "Authorized Lab Monitoring",
            },
        }
    )
    partial_alert = json.dumps(
        {
            "timestamp": "2026-04-07T08:19:15+00:00",
            "event_type": "alert",
            "src_ip": "10.1.0.9",
            "src_port": 49800,
            "dest_ip": "10.1.0.50",
            "dest_port": 8080,
            "proto": "TCP",
            "alert": {
                "severity": 3,
                "signature_id": 1000005,
                "signature": "AUTHORIZED LAB Demo staged marker event",
                "category": "Authorized Lab Monitoring",
            },
        }
    )

    with sample_alert_file.open("a", encoding="utf-8") as handle:
        handle.write(appended_alert + "\n")
        handle.write(partial_alert)

    second_result = alert_service.ingest_incremental_file(sample_alert_file)
    third_result = alert_service.ingest_incremental_file(sample_alert_file)

    assert second_result.total_lines == 1
    assert second_result.inserted_alerts == 1
    assert third_result.total_lines == 0
    assert third_result.inserted_alerts == 0

    with sample_alert_file.open("a", encoding="utf-8") as handle:
        handle.write("\n")

    fourth_result = alert_service.ingest_incremental_file(sample_alert_file)

    assert fourth_result.total_lines == 1
    assert fourth_result.inserted_alerts == 1

    stored_alerts = alert_service.list_alerts(limit=10)
    assert len(stored_alerts) == 4


def test_incremental_ingest_resets_after_truncation(alert_service: AlertService) -> None:
    long_line = json.dumps(
        {
            "timestamp": "2026-04-07T08:20:00+00:00",
            "event_type": "alert",
            "src_ip": "10.2.0.5",
            "src_port": 51514,
            "dest_ip": "10.2.0.10",
            "dest_port": 80,
            "proto": "TCP",
            "alert": {
                "severity": 2,
                "signature_id": 1000101,
                "signature": "AUTHORIZED LAB Demo long truncation baseline signature",
                "category": "Authorized Lab Monitoring",
            },
        }
    )
    short_line = json.dumps(
        {
            "timestamp": "2026-04-07T08:21:00+00:00",
            "event_type": "alert",
            "src_ip": "10.2.0.6",
            "src_port": 44321,
            "dest_ip": "10.2.0.20",
            "dest_port": 443,
            "proto": "TCP",
            "alert": {
                "severity": 1,
                "signature_id": 1000102,
                "signature": "AUTHORIZED LAB short",
                "category": "Authorized Lab Monitoring",
            },
        }
    )

    rotated_file = Path(alert_service.settings.suricata_log_path)
    rotated_file.write_text(long_line + "\n", encoding="utf-8")

    first_result = alert_service.ingest_incremental_file(rotated_file)
    assert first_result.inserted_alerts == 1

    rotated_file.write_text(short_line + "\n", encoding="utf-8")

    second_result = alert_service.ingest_incremental_file(rotated_file)

    assert second_result.read_offset_start == 0
    assert second_result.inserted_alerts == 1
    assert len(alert_service.list_alerts(limit=10)) == 2


def test_api_summary_and_alerts_return_expected_counts(
    client: TestClient,
    test_settings: Settings,
) -> None:
    service = AlertService(test_settings)
    service.ingest_sample_file()

    summary_response = client.get("/api/v1/summary")
    alerts_response = client.get("/api/v1/alerts")
    severity_response = client.get("/api/v1/alerts?severity=1")

    assert summary_response.status_code == 200
    assert alerts_response.status_code == 200
    assert severity_response.status_code == 200

    summary_payload = summary_response.json()
    alerts_payload = alerts_response.json()
    severity_payload = severity_response.json()

    assert summary_payload["total_alerts"] == 2
    assert len(summary_payload["alerts_by_severity"]) == 2
    assert len(alerts_payload) == 2
    assert len(severity_payload) == 1
    assert severity_payload[0]["severity"] == 1


def test_ingestion_status_and_runs_api_reflect_incremental_state(
    client: TestClient,
    test_settings: Settings,
) -> None:
    service = AlertService(test_settings)
    service.ingest_incremental_file(test_settings.suricata_log_path)
    service.ingest_incremental_file(test_settings.suricata_log_path)

    status_response = client.get("/api/v1/ingestion/status")
    runs_response = client.get("/api/v1/ingestion/runs?limit=5")

    assert status_response.status_code == 200
    assert runs_response.status_code == 200

    status_payload = status_response.json()
    runs_payload = runs_response.json()

    assert status_payload["last_run_mode"] == "incremental"
    assert status_payload["last_status"] == "no_new_data"
    assert status_payload["file_offset"] > 0
    assert status_payload["total_runs"] == 1
    assert len(runs_payload) == 1
    assert runs_payload[0]["mode"] == "incremental"
    assert runs_payload[0]["inserted_alerts"] == 2


def test_dashboard_shows_empty_state_when_no_alerts(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "No alerts loaded yet" in response.text
    assert "Authorized Lab Only" in response.text
    assert "Live Ingestion Status" in response.text
