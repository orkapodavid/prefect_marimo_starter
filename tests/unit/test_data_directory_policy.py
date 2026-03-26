from pathlib import Path
import subprocess


EXPECTED_TRACKED_DATA_PATHS = {
    "data/.gitkeep",
    "data/backups/postgres/.gitkeep",
    "data/dev/input/.gitkeep",
    "data/dev/output/.gitkeep",
    "data/financial_monitor/prod/.gitkeep",
    "data/input/.gitkeep",
    "data/ir_monitor/prod/.gitkeep",
    "data/output/.gitkeep",
    "data/output/tdnet_announcements/.gitkeep",
    "data/sample/.gitkeep",
    "data/x_monitor/twscrape/.gitkeep",
}

IGNORED_RUNTIME_PATHS = (
    "data/financial_monitor/prod/raw/edinet/S100TEST/report.zip",
    "data/ir_monitor/prod/generated/jobs.yaml",
    "data/output/tdnet_announcements/2026_03_26_japanese.csv",
    "data/prefect_home/prefect.db",
    "data/x_monitor/twscrape/accounts.db",
)


def test_data_directory_tracks_only_placeholder_structure():
    for path in EXPECTED_TRACKED_DATA_PATHS:
        assert Path(path).exists(), path

    result = subprocess.run(
        ["git", "ls-files", "data"],
        check=True,
        capture_output=True,
        text=True,
    )
    tracked_paths = {line for line in result.stdout.splitlines() if line}

    assert all(Path(path).name == ".gitkeep" for path in tracked_paths)
    assert tracked_paths.issubset(EXPECTED_TRACKED_DATA_PATHS)


def test_runtime_artifacts_under_data_are_gitignored():
    for path in IGNORED_RUNTIME_PATHS:
        result = subprocess.run(
            ["git", "check-ignore", path],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, path


def test_data_placeholders_remain_trackable():
    for path in EXPECTED_TRACKED_DATA_PATHS:
        assert Path(path).name == ".gitkeep"
        result = subprocess.run(
            ["git", "check-ignore", path],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1, path
