from pathlib import Path

from src.services.ir_monitor.ir_monitor_runner import run_webchanges_command
from src.services.ir_monitor.ir_monitor_models import WorkspacePaths


def test_run_webchanges_command_prepares_new_jobs_before_main_run(mocker, tmp_path: Path):
    workspace = WorkspacePaths(
        root_dir=tmp_path,
        generated_dir=tmp_path / "generated",
        jobs_path=tmp_path / "generated/jobs.yaml",
        config_path=tmp_path / "generated/config.yaml",
        state_dir=tmp_path / "state",
        artifacts_dir=tmp_path / "artifacts",
        logs_dir=tmp_path / "logs",
        changed_jobs_path=tmp_path / "artifacts/changed_jobs.json",
        baseline_metadata_path=tmp_path / "state/baselines.json",
    )
    for path in (
        workspace.generated_dir,
        workspace.state_dir,
        workspace.artifacts_dir,
        workspace.logs_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
    workspace.jobs_path.write_text("", encoding="utf-8")
    workspace.config_path.write_text("", encoding="utf-8")

    run_mock = mocker.patch("src.services.ir_monitor.ir_monitor_runner.subprocess.run")
    run_mock.side_effect = [
        mocker.Mock(returncode=0, stdout="", stderr=""),
        mocker.Mock(returncode=0, stdout="report", stderr=""),
    ]

    run_webchanges_command(workspace=workspace, new_target_ids=["mitsubishi_corp_ir_ja"])

    assert run_mock.call_count == 2


def test_run_webchanges_command_merges_existing_baseline_metadata(mocker, tmp_path: Path):
    workspace = WorkspacePaths(
        root_dir=tmp_path,
        generated_dir=tmp_path / "generated",
        jobs_path=tmp_path / "generated/jobs.yaml",
        config_path=tmp_path / "generated/config.yaml",
        state_dir=tmp_path / "state",
        artifacts_dir=tmp_path / "artifacts",
        logs_dir=tmp_path / "logs",
        changed_jobs_path=tmp_path / "artifacts/changed_jobs.json",
        baseline_metadata_path=tmp_path / "state/baselines.json",
    )
    for path in (
        workspace.generated_dir,
        workspace.state_dir,
        workspace.artifacts_dir,
        workspace.logs_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
    workspace.jobs_path.write_text("", encoding="utf-8")
    workspace.config_path.write_text("", encoding="utf-8")
    workspace.baseline_metadata_path.write_text(
        '{"baseline_target_ids": ["existing_target"]}',
        encoding="utf-8",
    )

    run_mock = mocker.patch("src.services.ir_monitor.ir_monitor_runner.subprocess.run")
    run_mock.side_effect = [
        mocker.Mock(returncode=0, stdout="", stderr=""),
        mocker.Mock(returncode=0, stdout="report", stderr=""),
    ]

    run_webchanges_command(workspace=workspace, new_target_ids=["new_target"])

    assert workspace.baseline_metadata_path.read_text(encoding="utf-8") == (
        '{\n  "baseline_target_ids": [\n    "existing_target",\n    "new_target"\n  ]\n}'
    )


def test_run_webchanges_command_does_not_record_baseline_when_prepare_fails(
    mocker, tmp_path: Path
):
    workspace = WorkspacePaths(
        root_dir=tmp_path,
        generated_dir=tmp_path / "generated",
        jobs_path=tmp_path / "generated/jobs.yaml",
        config_path=tmp_path / "generated/config.yaml",
        state_dir=tmp_path / "state",
        artifacts_dir=tmp_path / "artifacts",
        logs_dir=tmp_path / "logs",
        changed_jobs_path=tmp_path / "artifacts/changed_jobs.json",
        baseline_metadata_path=tmp_path / "state/baselines.json",
    )
    for path in (
        workspace.generated_dir,
        workspace.state_dir,
        workspace.artifacts_dir,
        workspace.logs_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
    workspace.jobs_path.write_text("", encoding="utf-8")
    workspace.config_path.write_text("", encoding="utf-8")
    workspace.baseline_metadata_path.write_text("{}", encoding="utf-8")

    run_mock = mocker.patch("src.services.ir_monitor.ir_monitor_runner.subprocess.run")
    run_mock.return_value = mocker.Mock(returncode=1, stdout="", stderr="prepare failed")

    run_webchanges_command(workspace=workspace, new_target_ids=["new_target"])

    assert workspace.baseline_metadata_path.read_text(encoding="utf-8") == "{}"
