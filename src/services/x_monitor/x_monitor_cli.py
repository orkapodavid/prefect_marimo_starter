"""Operator CLI for X monitor workflows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
from urllib.error import URLError
from urllib.request import urlopen

from sqlalchemy import text

from services.x_monitor.x_monitor_bootstrap import backfill_target, bootstrap_target
from services.x_monitor.x_monitor_config_loader import load_x_monitor_config
from services.x_monitor.x_monitor_database import get_x_monitor_engine
from services.x_monitor.x_monitor_gmail_api import (
    GmailApiProvider,
    build_gmail_api_credentials,
)
from services.x_monitor.x_monitor_gmail_smtp import GmailSmtpProvider
from services.x_monitor.x_monitor_targets_sync import sync_targets
from shared_utils.config import get_settings


def _build_email_provider(settings):
    provider_name = settings.x_monitor_gmail_provider
    if provider_name == "gmail_smtp":
        return GmailSmtpProvider(
            host=settings.x_monitor_gmail_smtp_host,
            port=settings.x_monitor_gmail_smtp_port,
            username=settings.x_monitor_gmail_smtp_username,
            password=settings.x_monitor_gmail_smtp_password,
            from_addr=settings.x_monitor_gmail_smtp_from,
            use_starttls=settings.x_monitor_gmail_smtp_use_starttls,
        )

    if provider_name == "gmail_api":
        credentials = build_gmail_api_credentials(
            credentials_file=settings.x_monitor_gmail_api_credentials_file,
            token_file=settings.x_monitor_gmail_api_token_file,
            use_adc=settings.x_monitor_gmail_api_use_adc,
        )
        return GmailApiProvider(
            credentials=credentials,
            from_addr=settings.x_monitor_gmail_api_from,
        )

    raise ValueError(f"Unsupported Gmail provider: {provider_name}")


def _build_twscrape_client(settings):
    from twscrape import API

    from services.x_monitor.x_monitor_twscrape_client import XMonitorTwscrapeClient

    api = API(db_file=str(settings.x_monitor_twscrape_accounts_db))
    return XMonitorTwscrapeClient(api=api)


def _print_json(payload: dict | list) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def _handle_sync_targets(args) -> int:
    config = load_x_monitor_config(Path(args.config))
    engine = get_x_monitor_engine()
    sync_targets(engine, [target.model_dump() for target in config.targets])
    _print_json({"status": "ok", "targets": len(config.targets)})
    return 0


def _handle_import_cookies(args) -> int:
    settings = get_settings()
    destination = settings.x_monitor_workspace_dir / "twscrape" / f"{args.username}_cookies.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.cookies_file, destination)
    _print_json({"status": "ok", "destination": str(destination)})
    return 0


def _handle_test_email(_args) -> int:
    settings = get_settings()
    recipients = [
        email.strip()
        for email in settings.x_monitor_operator_emails.split(",")
        if email.strip()
    ]
    if not recipients:
        raise ValueError("Set X_MONITOR_OPERATOR_EMAILS before using test-email")

    provider = _build_email_provider(settings)
    result = provider.send_email(
        to=[recipients[0]],
        subject=f"{settings.x_monitor_subject_prefix} Test email",
        text_body="X monitor test email",
        html_body="<p>X monitor test email</p>",
    )
    _print_json({"sent": result.sent, "error": result.error})
    return 0 if result.sent else 1


def _handle_bootstrap_targets(args) -> int:
    settings = get_settings()
    config = load_x_monitor_config(Path(args.config))
    engine = get_x_monitor_engine()
    client = _build_twscrape_client(settings)

    sync_targets(engine, [target.model_dump() for target in config.targets])
    results = [
        bootstrap_target(engine, client, target.model_dump())
        for target in config.targets
        if target.active
    ]
    _print_json(results)
    return 0


def _handle_backfill(args) -> int:
    settings = get_settings()
    config = load_x_monitor_config(Path(args.config))
    engine = get_x_monitor_engine()
    client = _build_twscrape_client(settings)

    selected_target = next(
        (target for target in config.targets if target.username == args.username),
        None,
    )
    if selected_target is None:
        raise ValueError(f"Unknown username in config: {args.username}")

    result = backfill_target(
        engine,
        client,
        selected_target.model_dump(),
        limit=args.limit,
    )
    _print_json(result)
    return 0


def _handle_health(_args) -> int:
    settings = get_settings()
    engine = get_x_monitor_engine()
    status = {
        "database": {"ok": False, "error": None},
        "prefect": {"ok": False, "error": None},
        "twscrape": {"ok": False, "error": None},
        "gmail_provider": settings.x_monitor_gmail_provider,
    }

    try:
        with engine.connect() as connection:
            connection.execute(text("select 1"))
        status["database"]["ok"] = True
    except Exception as exc:  # pragma: no cover - exercised in manual smoke tests
        status["database"]["error"] = str(exc)

    try:
        if settings.prefect_api_url:
            with urlopen(settings.prefect_api_url, timeout=5) as response:
                status["prefect"]["ok"] = 200 <= response.status < 500
        else:
            status["prefect"]["error"] = "PREFECT_API_URL is not configured"
    except URLError as exc:  # pragma: no cover - exercised in manual smoke tests
        status["prefect"]["error"] = str(exc)

    twscrape_path = settings.x_monitor_twscrape_accounts_db
    if twscrape_path.exists():
        status["twscrape"]["ok"] = True
    else:
        status["twscrape"]["error"] = f"Missing twscrape accounts DB: {twscrape_path}"

    _print_json(status)
    return 0 if all(part.get("ok") or part.get("error") is None for part in status.values() if isinstance(part, dict)) else 1


def _handle_migrate(_args) -> int:
    completed = subprocess.run(["alembic", "upgrade", "head"], check=False)
    return completed.returncode


def _handle_prefect_serve(_args) -> int:
    _print_json(
        {
            "status": "not_implemented",
            "message": "This repo uses notebook deployments with a local Prefect worker.",
        }
    )
    return 0


def _handle_init_db(_args) -> int:
    engine = get_x_monitor_engine()
    with engine.connect() as connection:
        connection.execute(text("select 1"))
    _print_json({"status": "ok"})
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the X monitor CLI parser."""
    parser = argparse.ArgumentParser(prog="python -m services.x_monitor.x_monitor_cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_targets_parser = subparsers.add_parser("sync-targets")
    sync_targets_parser.add_argument(
        "--config",
        default=str(get_settings().x_monitor_config_path),
    )
    sync_targets_parser.set_defaults(handler=_handle_sync_targets)

    import_cookies_parser = subparsers.add_parser("import-cookies")
    import_cookies_parser.add_argument("--cookies-file", required=True)
    import_cookies_parser.add_argument("--username", required=True)
    import_cookies_parser.set_defaults(handler=_handle_import_cookies)

    test_email_parser = subparsers.add_parser("test-email")
    test_email_parser.set_defaults(handler=_handle_test_email)

    bootstrap_parser = subparsers.add_parser("bootstrap-targets")
    bootstrap_parser.add_argument(
        "--config",
        default=str(get_settings().x_monitor_config_path),
    )
    bootstrap_parser.set_defaults(handler=_handle_bootstrap_targets)

    backfill_parser = subparsers.add_parser("backfill")
    backfill_parser.add_argument("--config", default=str(get_settings().x_monitor_config_path))
    backfill_parser.add_argument("--username", required=True)
    backfill_parser.add_argument("--limit", type=int, default=100)
    backfill_parser.set_defaults(handler=_handle_backfill)

    health_parser = subparsers.add_parser("health")
    health_parser.set_defaults(handler=_handle_health)

    migrate_parser = subparsers.add_parser("migrate")
    migrate_parser.set_defaults(handler=_handle_migrate)

    init_db_parser = subparsers.add_parser("init-db")
    init_db_parser.set_defaults(handler=_handle_init_db)

    prefect_serve_parser = subparsers.add_parser("prefect-serve")
    prefect_serve_parser.set_defaults(handler=_handle_prefect_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
