from __future__ import annotations

from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ids_dashboard.core.config import Settings  # noqa: E402
from ids_dashboard.main import create_app  # noqa: E402
from ids_dashboard.services.alerts import AlertService  # noqa: E402


@pytest.fixture
def sample_alert_lines() -> list[str]:
    return [
        (
            '{"timestamp":"2026-04-07T08:15:30+00:00","event_type":"alert",'
            '"src_ip":"10.1.0.5","src_port":51514,"dest_ip":"10.1.0.10",'
            '"dest_port":80,"proto":"TCP","alert":{"severity":2,'
            '"signature_id":1000001,"signature":"AUTHORIZED LAB Demo HTTP marker '
            'detected","category":"Authorized Lab Monitoring"}}'
        ),
        (
            '{"timestamp":"2026-04-07T08:15:30+00:00","event_type":"alert",'
            '"src_ip":"10.1.0.5","src_port":51514,"dest_ip":"10.1.0.10",'
            '"dest_port":80,"proto":"TCP","alert":{"severity":2,'
            '"signature_id":1000001,"signature":"AUTHORIZED LAB Demo HTTP marker '
            'detected","category":"Authorized Lab Monitoring"}}'
        ),
        (
            '{"timestamp":"2026-04-07T08:16:01+00:00","event_type":"dns",'
            '"src_ip":"10.1.0.6","src_port":53022,"dest_ip":"10.1.0.20",'
            '"dest_port":53,"proto":"UDP","dns":{"rrname":"training.invalid"}}'
        ),
        (
            '{"timestamp":"2026-04-07T08:17:42+00:00","event_type":"alert",'
            '"src_ip":"10.1.0.7","src_port":44321,"dest_ip":"10.1.0.30",'
            '"dest_port":443,"proto":"TCP","alert":{"severity":1,'
            '"signature_id":1000003,"signature":"AUTHORIZED LAB Demo self-signed '
            'certificate observed","category":"Authorized Lab Monitoring"}}'
        ),
    ]


@pytest.fixture
def sample_alert_file(tmp_path: Path, sample_alert_lines: list[str]) -> Path:
    file_path = tmp_path / "suricata_test_eve.json"
    file_path.write_text("\n".join(sample_alert_lines) + "\n", encoding="utf-8")
    return file_path


@pytest.fixture
def test_settings(tmp_path: Path, sample_alert_file: Path) -> Settings:
    return Settings(
        app_env="test",
        log_level="DEBUG",
        database_url=f"sqlite:///{tmp_path / 'ids_dashboard_test.db'}",
        suricata_eve_log_path=str(sample_alert_file),
    )


@pytest.fixture
def alert_service(test_settings: Settings) -> AlertService:
    return AlertService(test_settings)


@pytest.fixture
def client(test_settings: Settings) -> TestClient:
    app = create_app(test_settings)
    with TestClient(app) as test_client:
        yield test_client

