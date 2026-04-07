"""Allow `python -m ids_dashboard` to run the CLI."""

from __future__ import annotations

from ids_dashboard.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
