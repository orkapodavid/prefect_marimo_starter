from pathlib import Path

import pytest

from src.services.x_monitor.x_monitor_config_loader import load_x_monitor_config


def test_load_x_monitor_config_applies_defaults(tmp_path: Path):
    config_path = tmp_path / "targets.yaml"
    config_path.write_text(
        """
runtime:
  timezone: Asia/Hong_Kong
  poll_batch_limit: 10
  immediate_alerts_enabled: true
  daily_digest_enabled: true
  subject_prefix: "[X Monitor]"
defaults:
  include_replies: false
  include_retweets: false
  media_only: false
targets:
  - id: openai_posts
    username: openai
    keywords_any: ["launch"]
    alert_recipients: ["alerts@example.com"]
    digest_recipients: ["digest@example.com"]
""",
        encoding="utf-8",
    )

    config = load_x_monitor_config(config_path)

    assert config.runtime.timezone == "Asia/Hong_Kong"
    assert config.runtime.poll_batch_limit == 10
    assert config.runtime.immediate_alerts_enabled is True
    assert config.runtime.daily_digest_enabled is True
    assert config.runtime.subject_prefix == "[X Monitor]"
    assert config.targets[0].include_replies is False
    assert config.targets[0].include_retweets is False
    assert config.targets[0].media_only is False
    assert config.targets[0].active is True
    assert config.targets[0].keywords_any == ["launch"]


def test_load_x_monitor_config_rejects_duplicate_ids(tmp_path: Path):
    config_path = tmp_path / "targets.yaml"
    config_path.write_text(
        """
targets:
  - id: duplicate_target
    username: account_one
    alert_recipients: ["alerts@example.com"]
    digest_recipients: ["digest@example.com"]
  - id: duplicate_target
    username: account_two
    alert_recipients: ["alerts@example.com"]
    digest_recipients: ["digest@example.com"]
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_x_monitor_config(config_path)


def test_load_x_monitor_config_no_rules_means_match_all(tmp_path: Path):
    config_path = tmp_path / "targets.yaml"
    config_path.write_text(
        """
targets:
  - id: catch_all
    username: some_account
    alert_recipients: ["alerts@example.com"]
    digest_recipients: ["digest@example.com"]
""",
        encoding="utf-8",
    )

    config = load_x_monitor_config(config_path)
    target = config.targets[0]

    assert target.keywords_any == []
    assert target.keywords_all == []
    assert target.regex_any == []


def test_load_x_monitor_config_resolves_repo_relative_path_outside_repo_cwd(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)

    config = load_x_monitor_config(Path("./config/x_monitor/x_monitor_targets.yaml"))

    assert config.runtime.timezone == "Asia/Singapore"
    assert config.targets[0].username == "openai"
    assert config.targets[1].username == "nvidia"
