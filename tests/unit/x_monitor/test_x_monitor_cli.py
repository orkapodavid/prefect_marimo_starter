from src.services.x_monitor.x_monitor_cli import build_parser


def test_cli_exposes_required_subcommands():
    parser = build_parser()
    subcommands = parser._subparsers._group_actions[0].choices

    assert "sync-targets" in subcommands
    assert "import-cookies" in subcommands
    assert "test-email" in subcommands
    assert "bootstrap-targets" in subcommands
    assert "backfill" in subcommands
    assert "health" in subcommands
