"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ids_dashboard import __version__
from ids_dashboard.api.errors import register_error_handlers
from ids_dashboard.api.routes import router as api_router
from ids_dashboard.core.config import Settings, get_settings
from ids_dashboard.core.logging import configure_logging
from ids_dashboard.services.alerts import AlertService
from ids_dashboard.services.live_ingestion import LiveIngestionWatcher
from ids_dashboard.web.routes import router as web_router


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""

    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)

    alert_service = AlertService(resolved_settings)
    templates = Jinja2Templates(directory=str(resolved_settings.templates_dir))
    live_ingestion_watcher = (
        LiveIngestionWatcher(
            alert_service,
            poll_interval_seconds=resolved_settings.live_ingestion_poll_interval_seconds,
        )
        if resolved_settings.enable_live_ingestion
        else None
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = resolved_settings
        app.state.alert_service = alert_service
        app.state.templates = templates
        app.state.live_ingestion_watcher = live_ingestion_watcher
        alert_service.initialize_database()
        if live_ingestion_watcher is not None:
            live_ingestion_watcher.start()
        yield
        if live_ingestion_watcher is not None:
            live_ingestion_watcher.stop()

    app = FastAPI(
        title=resolved_settings.app_name,
        version=__version__,
        description=(
            "Defensive, authorized-lab Suricata alert dashboard for portfolio demos."
        ),
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.alert_service = alert_service
    app.state.templates = templates
    app.state.live_ingestion_watcher = live_ingestion_watcher

    app.mount(
        "/static",
        StaticFiles(directory=str(resolved_settings.static_dir)),
        name="static",
    )
    register_error_handlers(app)
    app.include_router(api_router)
    app.include_router(web_router)
    return app


app = create_app()
