from pathlib import Path
import subprocess
import sys


def test_normalize_script_runs_with_generic_jp_normalizer():
    html_path = Path("tests/fixtures/ir_monitor/html/jp_ir_list.html")
    result = subprocess.run(
        [
            sys.executable,
            "scripts/ir_monitor/ir_monitor_normalize_content.py",
            "--normalizer",
            "generic_jp_ir_news",
            "--page-url",
            "https://example.co.jp/jp/ir/",
            "--input-file",
            str(html_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "ITEM_KEY=" in result.stdout


def test_normalize_script_exits_non_zero_for_unknown_normalizer():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/ir_monitor/ir_monitor_normalize_content.py",
            "--normalizer",
            "unknown_normalizer",
            "--page-url",
            "https://example.co.jp/jp/ir/",
        ],
        check=False,
        capture_output=True,
        text=True,
        input="<html></html>",
    )

    assert result.returncode != 0
