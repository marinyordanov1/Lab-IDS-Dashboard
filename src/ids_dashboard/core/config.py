"""Environment-backed application configuration."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os

from ids_dashboard.core.exceptions import ConfigurationError


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATABASE_URL = "sqlite:///data/ids_dashboard.db"
DEFAULT_SURICATA_LOG_PATH = "data/sample/suricata_eve.json"
DEFAULT_LIVE_INGESTION_POLL_INTERVAL_SECONDS = 2.0
DEFAULT_DASHBOARD_AUTO_REFRESH_SECONDS = 5
SUPPORTED_ENVIRONMENTS = {"development", "test", "production"}


def _load_dotenv_values(env_path: Path) -> dict[str, str]:
    """Parse a simple local `.env` file if present."""

    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, raw_value = stripped.split("=", 1)
        values[key.strip()] = raw_value.strip().strip("\"'")
    return values


def _parse_bool(raw_value: str | bool) -> bool:
    """Parse a boolean-ish environment value."""

    if isinstance(raw_value, bool):
        return raw_value
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    """Application settings loaded from environment variables."""

    app_name: str = "Authorized Lab IDS Dashboard"
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = DEFAULT_DATABASE_URL
    suricata_eve_log_path: str = DEFAULT_SURICATA_LOG_PATH
    enable_live_ingestion: bool = False
    live_ingestion_poll_interval_seconds: float = (
        DEFAULT_LIVE_INGESTION_POLL_INTERVAL_SECONDS
    )
    dashboard_auto_refresh_seconds: int = DEFAULT_DASHBOARD_AUTO_REFRESH_SECONDS

    def __post_init__(self) -> None:
        normalized_env = self.app_env.lower()
        if normalized_env not in SUPPORTED_ENVIRONMENTS:
            raise ConfigurationError(
                f"APP_ENV must be one of {sorted(SUPPORTED_ENVIRONMENTS)}."
            )
        if not self.database_url.startswith("sqlite:///"):
            raise ConfigurationError("DATABASE_URL must use the sqlite:/// scheme.")
        if self.live_ingestion_poll_interval_seconds <= 0:
            raise ConfigurationError(
                "LIVE_INGEST_POLL_INTERVAL_SECONDS must be greater than 0."
            )
        if self.dashboard_auto_refresh_seconds < 0:
            raise ConfigurationError(
                "DASHBOARD_AUTO_REFRESH_SECONDS must be 0 or greater."
            )

        object.__setattr__(self, "app_env", normalized_env)
        object.__setattr__(self, "log_level", self.log_level.upper())

    @property
    def database_target(self) -> str:
        """Return the SQLite database target path for `sqlite3.connect`."""

        raw_target = self.database_url.removeprefix("sqlite:///")
        if raw_target == ":memory:":
            return raw_target

        target_path = Path(raw_target).expanduser()
        if not target_path.is_absolute():
            target_path = PROJECT_ROOT / target_path
        return str(target_path)

    @property
    def suricata_log_path(self) -> Path:
        """Return the resolved Suricata alert log path."""

        candidate = Path(self.suricata_eve_log_path).expanduser()
        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate
        return candidate

    @property
    def templates_dir(self) -> Path:
        """Return the Jinja template directory."""

        return PROJECT_ROOT / "src" / "ids_dashboard" / "web" / "templates"

    @property
    def static_dir(self) -> Path:
        """Return the static assets directory."""

        return PROJECT_ROOT / "src" / "ids_dashboard" / "web" / "static"

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables."""

        dotenv_values = _load_dotenv_values(PROJECT_ROOT / ".env")
        return cls(
            app_env=os.getenv("APP_ENV", dotenv_values.get("APP_ENV", "development")),
            log_level=os.getenv("LOG_LEVEL", dotenv_values.get("LOG_LEVEL", "INFO")),
            database_url=os.getenv(
                "DATABASE_URL",
                dotenv_values.get("DATABASE_URL", DEFAULT_DATABASE_URL),
            ),
            suricata_eve_log_path=os.getenv(
                "SURICATA_EVE_LOG_PATH",
                dotenv_values.get(
                    "SURICATA_EVE_LOG_PATH",
                    DEFAULT_SURICATA_LOG_PATH,
                ),
            ),
            enable_live_ingestion=_parse_bool(
                os.getenv(
                    "ENABLE_LIVE_INGESTION",
                    dotenv_values.get("ENABLE_LIVE_INGESTION", "false"),
                )
            ),
            live_ingestion_poll_interval_seconds=float(
                os.getenv(
                    "LIVE_INGEST_POLL_INTERVAL_SECONDS",
                    dotenv_values.get(
                        "LIVE_INGEST_POLL_INTERVAL_SECONDS",
                        str(DEFAULT_LIVE_INGESTION_POLL_INTERVAL_SECONDS),
                    ),
                )
            ),
            dashboard_auto_refresh_seconds=int(
                os.getenv(
                    "DASHBOARD_AUTO_REFRESH_SECONDS",
                    dotenv_values.get(
                        "DASHBOARD_AUTO_REFRESH_SECONDS",
                        str(DEFAULT_DASHBOARD_AUTO_REFRESH_SECONDS),
                    ),
                )
            ),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings.from_env()
