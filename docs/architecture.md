# Architecture Notes

## Goals

- Keep the project runnable without Suricata installed by shipping sample data.
- Preserve a clean separation between parsing, persistence, API, and UI.
- Use defensive-only sample data and demo rules.
- Support safe, local, incremental polling of a lab `eve.json` file.

## Request and Data Flow

1. A CLI command reads a Suricata `eve.json` file.
2. The parser validates alert events, normalizes timestamps to UTC, and computes a stable fingerprint.
3. The service stores alerts in SQLite with deduplication on the fingerprint.
4. Incremental ingestion stores file offsets and ingestion run history in SQLite.
5. FastAPI exposes read-only JSON endpoints and a simple dashboard over the stored data.

## Main Components

- `core/`: configuration, logging, and shared exceptions
- `ingestion/`: Suricata alert parsing and normalized models
- `db/`: SQLite schema and repository access
- `services/`: orchestration for ingestion and reporting
- `services/live_ingestion.py`: background polling watcher for local lab logs
- `api/`: REST routes and API error handling
- `web/`: dashboard template and static styling

## Security and Scope Controls

- Only `event_type == "alert"` records are ingested.
- Input is validated before storage.
- SQLite queries use bound parameters.
- Incremental ingestion advances offsets only past newline-terminated records.
- The UI and README clearly mark the project as authorized lab-only.
- No traffic generation, offensive simulation, or unauthorized capture is included.
