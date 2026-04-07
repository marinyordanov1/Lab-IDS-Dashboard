"""Command-line interface for database initialization and ingestion."""

from __future__ import annotations

import argparse
import logging
import time

from ids_dashboard.core.config import get_settings
from ids_dashboard.core.exceptions import AppError
from ids_dashboard.core.logging import configure_logging
from ids_dashboard.ingestion.models import IngestionResult
from ids_dashboard.services.alerts import AlertService


logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(
        prog="authorized-lab-ids-dashboard",
        description="Authorized lab Suricata alert ingestion utilities.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="Initialize the SQLite schema.")
    subparsers.add_parser(
        "ingest-sample",
        help="Ingest the bundled safe sample Suricata eve.json file.",
    )
    ingest_file_parser = subparsers.add_parser(
        "ingest-file",
        help="Ingest alerts from a local Suricata eve.json file.",
    )
    ingest_file_parser.add_argument("--path", required=True, help="Path to eve.json.")
    ingest_file_parser.add_argument(
        "--incremental",
        action="store_true",
        help="Only ingest newly appended complete lines since the last recorded offset.",
    )

    watch_file_parser = subparsers.add_parser(
        "watch-file",
        help="Continuously poll a local Suricata eve.json file for new complete lines.",
    )
    watch_file_parser.add_argument("--path", required=True, help="Path to eve.json.")
    watch_file_parser.add_argument(
        "--poll-interval",
        type=float,
        default=None,
        help="Seconds between incremental polling cycles.",
    )
    watch_file_parser.add_argument(
        "--max-cycles",
        type=int,
        default=None,
        help="Optional finite number of polling cycles for demos or tests.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return an exit code."""

    settings = get_settings()
    configure_logging(settings.log_level)
    parser = build_parser()
    args = parser.parse_args(argv)
    service = AlertService(settings)

    try:
        if args.command == "init-db":
            service.initialize_database()
            print(f"Initialized SQLite database at {settings.database_target}")
            return 0

        if args.command == "watch-file":
            poll_interval = (
                args.poll_interval
                if args.poll_interval is not None
                else settings.live_ingestion_poll_interval_seconds
            )
            cycle_count = 0
            while True:
                result = service.ingest_incremental_file(args.path)
                print(_format_ingestion_result(result))
                cycle_count += 1
                if args.max_cycles is not None and cycle_count >= args.max_cycles:
                    return 0
                time.sleep(poll_interval)

        if args.command == "ingest-sample":
            result = service.ingest_sample_file()
        else:
            result = service.ingest_file(args.path, incremental=args.incremental)

        print(_format_ingestion_result(result))
        return 0
    except KeyboardInterrupt:
        print("Watcher stopped by user.")
        return 0
    except AppError as exc:
        logger.error("%s", exc.message)
        return 1


def _format_ingestion_result(result: IngestionResult) -> str:
    return (
        f"{result.mode} ingestion complete: "
        f"lines={result.total_lines}, "
        f"parsed={result.parsed_alerts}, "
        f"inserted={result.inserted_alerts}, "
        f"duplicates={result.duplicate_alerts}, "
        f"skipped={result.skipped_lines}, "
        f"errors={result.error_lines}, "
        f"offset={result.read_offset_start}->{result.read_offset_end}"
    )
