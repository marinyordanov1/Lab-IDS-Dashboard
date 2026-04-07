"""REST API routes."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from ids_dashboard.api.schemas import (
    AlertOut,
    IngestionRunOut,
    IngestionStatusOut,
    SummaryOut,
)
from ids_dashboard.core.config import Settings
from ids_dashboard.services.alerts import AlertService


router = APIRouter()


def _get_alert_service(request: Request) -> AlertService:
    return request.app.state.alert_service


def _get_settings(request: Request) -> Settings:
    return request.app.state.settings


def _get_watcher_snapshot(request: Request) -> dict[str, object] | None:
    watcher = getattr(request.app.state, "live_ingestion_watcher", None)
    return watcher.snapshot() if watcher else None


@router.get("/health")
def health(request: Request) -> dict[str, str]:
    """Return a simple application health response."""

    settings = _get_settings(request)
    return {
        "status": "ok",
        "environment": settings.app_env,
        "database": settings.database_target,
    }


@router.get("/api/v1/alerts", response_model=list[AlertOut])
def list_alerts(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
    severity: int | None = Query(default=None, ge=1, le=5),
    signature: str | None = Query(default=None, min_length=1, max_length=200),
) -> list[dict[str, object]]:
    """Return recent alerts with optional filters."""

    service = _get_alert_service(request)
    return service.list_alerts(limit=limit, severity=severity, signature=signature)


@router.get("/api/v1/summary", response_model=SummaryOut)
def get_summary(request: Request) -> dict[str, object]:
    """Return aggregate alert statistics."""

    service = _get_alert_service(request)
    return service.get_summary()


@router.get("/api/v1/ingestion/status", response_model=IngestionStatusOut)
def get_ingestion_status(request: Request) -> dict[str, object]:
    """Return current ingestion status for the configured source path."""

    service = _get_alert_service(request)
    watcher_snapshot = _get_watcher_snapshot(request)
    return service.get_ingestion_status(watcher_snapshot=watcher_snapshot)


@router.get("/api/v1/ingestion/runs", response_model=list[IngestionRunOut])
def list_ingestion_runs(
    request: Request,
    limit: int = Query(default=10, ge=1, le=50),
) -> list[dict[str, object]]:
    """Return recent ingestion runs for the configured source path."""

    service = _get_alert_service(request)
    return service.list_ingestion_runs(limit=limit)
