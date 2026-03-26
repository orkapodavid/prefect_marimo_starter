from pathlib import Path
import subprocess

from src.services.ir_monitor.ir_monitor_jobs_builder import build_workspace_files
from src.services.ir_monitor.ir_monitor_models import MonitorConfig, MonitorDefaults, MonitorTarget
from src.shared_utils.paths import get_repo_root


def test_build_workspace_files_writes_jobs_config_and_state_paths(tmp_path: Path):
    config = MonitorConfig(
        defaults=MonitorDefaults(timezone="Asia/Tokyo", report_timezone="Asia/Tokyo"),
        targets=[
            MonitorTarget(
                id="mitsubishi_corp_ir_ja",
                company_id="mitsubishi_corp",
                company_name="Mitsubishi Corporation",
                page_label="Japanese IR page",
                page_url="https://example.co.jp/jp/ir/",
                user_visible_url="https://example.co.jp/jp/ir/",
                target_kind="html_list",
                selector_type="custom_script",
                normalizer="generic_jp_ir_news",
                enabled=True,
            ),
            MonitorTarget(
                id="mitsubishi_corp_ir_ja_alt",
                company_id="mitsubishi_corp",
                company_name="Mitsubishi Corporation",
                page_label="Japanese IR page alt",
                page_url="https://example.co.jp/jp/ir/",
                user_visible_url="https://example.co.jp/jp/ir/",
                target_kind="html_list",
                selector_type="custom_script",
                normalizer="generic_jp_ir_news",
                enabled=True,
            ),
        ],
    )

    workspace = build_workspace_files(config=config, workspace_dir=tmp_path)

    assert workspace.jobs_path.exists()
    assert workspace.config_path.exists()
    assert workspace.state_dir.exists()
    jobs_text = workspace.jobs_path.read_text(encoding="utf-8")
    config_text = workspace.config_path.read_text(encoding="utf-8")
    assert "user_visible_url" in jobs_text
    assert jobs_text.count("https://example.co.jp/jp/ir/") >= 1
    assert "stdout" in config_text
    assert "run_command" not in config_text


def test_build_workspace_files_preserves_existing_baseline_metadata(tmp_path: Path):
    config = MonitorConfig(
        defaults=MonitorDefaults(timezone="Asia/Tokyo", report_timezone="Asia/Tokyo"),
        targets=[
            MonitorTarget(
                id="mitsubishi_corp_ir_ja",
                company_id="mitsubishi_corp",
                company_name="Mitsubishi Corporation",
                page_label="Japanese IR page",
                page_url="https://example.co.jp/jp/ir/",
                user_visible_url="https://example.co.jp/jp/ir/",
                target_kind="html_list",
                selector_type="custom_script",
                normalizer="generic_jp_ir_news",
                enabled=True,
            )
        ],
    )
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    baseline_metadata_path = state_dir / "baselines.json"
    baseline_metadata_path.write_text(
        '{"baseline_target_ids": ["mitsubishi_corp_ir_ja"]}',
        encoding="utf-8",
    )

    workspace = build_workspace_files(config=config, workspace_dir=tmp_path)

    assert workspace.baseline_metadata_path.read_text(encoding="utf-8") == (
        '{"baseline_target_ids": ["mitsubishi_corp_ir_ja"]}'
    )


def test_build_workspace_files_generates_webchanges_valid_job_and_config_yaml(tmp_path: Path):
    config = MonitorConfig(
        defaults=MonitorDefaults(timezone="Asia/Tokyo", report_timezone="Asia/Tokyo"),
        targets=[
            MonitorTarget(
                id="mitsubishi_corp_ir_ja",
                company_id="mitsubishi_corp",
                company_name="Mitsubishi Corporation",
                page_label="Japanese IR page",
                page_url="https://example.co.jp/jp/ir/",
                user_visible_url="https://example.co.jp/jp/ir/",
                target_kind="html_list",
                selector_type="custom_script",
                normalizer="generic_jp_ir_news",
                enabled=True,
            )
        ],
    )

    workspace = build_workspace_files(config=config, workspace_dir=tmp_path)

    result = subprocess.run(
        [
            "uv",
            "run",
            "webchanges",
            "--jobs",
            str(workspace.jobs_path),
            "--config",
            str(workspace.config_path),
            "--database",
            str(workspace.state_dir / "snapshots.db"),
            "--test",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_build_workspace_files_resolves_normalizer_script_from_repo_root(
    tmp_path: Path,
    monkeypatch,
):
    config = MonitorConfig(
        defaults=MonitorDefaults(timezone="Asia/Tokyo", report_timezone="Asia/Tokyo"),
        targets=[
            MonitorTarget(
                id="mitsubishi_corp_ir_ja",
                company_id="mitsubishi_corp",
                company_name="Mitsubishi Corporation",
                page_label="Japanese IR page",
                page_url="https://example.co.jp/jp/ir/",
                user_visible_url="https://example.co.jp/jp/ir/",
                target_kind="html_list",
                selector_type="custom_script",
                normalizer="generic_jp_ir_news",
                enabled=True,
            )
        ],
    )
    monkeypatch.chdir(tmp_path)

    workspace = build_workspace_files(config=config, workspace_dir=tmp_path / "workspace")
    jobs_text = workspace.jobs_path.read_text(encoding="utf-8")

    assert str(get_repo_root() / "scripts/ir_monitor/ir_monitor_normalize_content.py") in jobs_text
