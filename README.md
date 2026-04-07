# Authorized Lab IDS Dashboard

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Scope: Defensive Lab Only](https://img.shields.io/badge/scope-defensive%20lab%20only-0e5a43)](./SECURITY.md)

Authorized Lab IDS Dashboard is a defensive cybersecurity portfolio project for an authorized lab environment. It ingests safe Suricata `eve.json` alerts, normalizes them into SQLite, and presents a lightweight dashboard plus REST API for triage-oriented visibility. Phase 2 adds incremental ingestion state, optional local file watching, and dashboard auto-refresh for a more realistic analyst demo.

## Safety Warning

- This project is strictly for defensive, educational, and authorized lab use.
- Do not use it to monitor networks you do not own or administer with explicit permission.
- This repository intentionally excludes offensive functionality, exploit delivery, bypasses, persistence, credential access, or unauthorized scanning.
- The bundled rules and sample logs are safe demo artifacts only.

## Project Overview

The MVP is designed to simulate a small SOC visibility workflow:

- ingest structured IDS alerts from Suricata `eve.json`
- normalize and deduplicate alert events
- store alerts in SQLite with secure defaults
- track incremental ingestion offsets and recent ingestion runs
- expose read-only REST endpoints for alert review
- render a demo-friendly dashboard with summary metrics, ingestion status, and a recent alert timeline

## Highlights

- Defensive-only IDS alert pipeline focused on authorized lab telemetry.
- Clean Python project structure with modular services, tests, docs, and sample data.
- GitHub-ready repository hygiene with CI, issue templates, PR template, MIT license, and contributor/security guidance.
- Beginner-friendly local development using FastAPI, SQLite, and synthetic Suricata `eve.json` samples.

## Business Value

- Demonstrates SOC-style alert triage and analyst workflow familiarity.
- Shows how detection telemetry can be normalized into a reporting pipeline.
- Provides a beginner-friendly but production-style Python codebase with modular services, validation, testing, logging, and documentation.
- Creates a strong portfolio artifact for security engineering, blue-team, or security analyst roles.

## Architecture

```text
Suricata eve.json (sample or local lab log)
        |
        v
Parser + validation + UTC normalization + fingerprinting
        |
        v
SQLite alert store
        |
        +--> Ingestion state + run history
        |
        +--> Optional local file watcher (authorized lab only)
        |
        +--> FastAPI REST API (/health, /api/v1/alerts, /api/v1/summary)
        |
        +--> Server-rendered dashboard (/)
```

Additional architecture notes are in [docs/architecture.md](docs/architecture.md).

## Folder Structure

```text
.
├── app.py
├── manage.py
├── config/
│   └── suricata/
├── data/
│   └── sample/
├── docs/
├── src/
│   └── ids_dashboard/
└── tests/
```

## Tech Stack

- Python 3.12+
- FastAPI for API and web serving
- Jinja2 for the server-rendered dashboard
- SQLite for local persistence
- Pytest for unit and integration testing

## Quick Start

```bash
make setup
cp .env.example .env
make init-db
make ingest-sample
make run
```

Then open `http://127.0.0.1:8000/`.

## Setup Instructions

1. Create a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy the environment file if you want to customize paths:

   ```bash
   cp .env.example .env
   ```

## Usage

Initialize the database:

```bash
python manage.py init-db
```

Ingest the bundled safe sample alerts:

```bash
python manage.py ingest-sample
```

Run the dashboard:

```bash
uvicorn app:app --reload
```

Then open `http://127.0.0.1:8000/`.

## Live Local Ingestion

The dashboard can now poll a local Suricata `eve.json` file for newly appended complete lines. This is intended only for an authorized local lab.

Enable it in `.env`:

```bash
ENABLE_LIVE_INGESTION=true
SURICATA_EVE_LOG_PATH=/absolute/path/to/eve.json
LIVE_INGEST_POLL_INTERVAL_SECONDS=2
DASHBOARD_AUTO_REFRESH_SECONDS=5
```

Then run the app:

```bash
uvicorn app:app --reload
```

You can also run the watcher from the CLI:

```bash
python manage.py watch-file --path /absolute/path/to/eve.json --poll-interval 2
```

Or do one incremental import pass:

```bash
python manage.py ingest-file --path /absolute/path/to/eve.json --incremental
```

## REST API

- `GET /health`
- `GET /api/v1/alerts`
- `GET /api/v1/summary`
- `GET /api/v1/ingestion/status`
- `GET /api/v1/ingestion/runs`

Example:

```bash
curl "http://127.0.0.1:8000/api/v1/alerts?limit=10"
```

## Rule and Configuration Approach

- Phase 1 targets Suricata because `eve.json` is structured and easier to normalize safely.
- The repo includes a safe `config/suricata/local.rules` example with benign lab-only markers.
- The repo also includes `config/suricata/suricata.yaml.example` showing the `eve-log` output configuration needed for alert ingestion.
- Suricata itself is optional for the MVP because the project ships with sample logs.

## Screenshots and Demo Ideas

- Capture the empty-state dashboard before ingestion.
- Run `python manage.py ingest-sample` and capture the populated dashboard.
- Demonstrate `GET /api/v1/summary` alongside the UI to show backend/frontend consistency.
- Walk through the safe custom rules and explain how they map to benign lab markers.

## Testing

Run the full test suite:

```bash
pytest
```

or

```bash
make test
```

Recommended checks:

- parser unit tests pass
- duplicate alerts are ignored in SQLite
- incremental imports only read newly appended complete lines
- ingestion status and run history update after local polling
- `/api/v1/alerts` and `/api/v1/summary` return expected counts
- dashboard empty state renders before ingestion

## Limitations

- Live ingestion is polling-based for local lab use; it is not a distributed ingestion pipeline.
- Only Suricata `eve.json` alert events are supported in the MVP.
- Alert enrichment, analyst notes, and authentication are intentionally out of scope.
- SQLite is appropriate for local development and demos, not multi-user production deployment.

## Future Improvements

- dashboard filtering, pagination, and export
- Snort adapter support
- analyst notes and alert workflow states
- Docker or devcontainer support
- richer detection engineering documentation and rule validation

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development expectations and safety guardrails.

## Security

See [SECURITY.md](./SECURITY.md) for reporting guidance and repository scope restrictions.

## License

This project is licensed under the [MIT License](./LICENSE).
