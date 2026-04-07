"""Server-rendered dashboard routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    """Render the dashboard homepage."""

    service = request.app.state.alert_service
    templates = request.app.state.templates
    settings = request.app.state.settings
    watcher = getattr(request.app.state, "live_ingestion_watcher", None)

    summary = service.get_summary()
    alerts = service.list_alerts(limit=20)
    ingestion_status = service.get_ingestion_status(
        watcher_snapshot=watcher.snapshot() if watcher else None
    )
    ingestion_runs = service.list_ingestion_runs(limit=5)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "page_title": "Authorized Lab IDS Dashboard",
            "summary": summary,
            "alerts": alerts,
            "ingestion_status": ingestion_status,
            "ingestion_runs": ingestion_runs,
            "auto_refresh_enabled": settings.enable_live_ingestion
            and settings.dashboard_auto_refresh_seconds > 0,
            "auto_refresh_seconds": settings.dashboard_auto_refresh_seconds,
            "has_alerts": summary["total_alerts"] > 0,
            "generated_at": datetime.now(timezone.utc).isoformat().replace(
                "+00:00",
                "Z",
            ),
        },
    )
