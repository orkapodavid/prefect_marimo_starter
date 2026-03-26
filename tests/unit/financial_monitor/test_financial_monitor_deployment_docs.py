from pathlib import Path

import yaml


def test_prefect_yaml_contains_financial_monitor_deployment():
    prefect_yaml = Path("prefect.yaml").read_text(encoding="utf-8")
    prefect_config = yaml.safe_load(prefect_yaml)
    deployments = {deployment["name"]: deployment for deployment in prefect_config["deployments"]}
    deployment = deployments["financial-monitor-daily-prod"]

    assert "financial-monitor-daily-prod" in prefect_yaml
    assert (
        "notebooks/financial_monitor/financial_monitor_daily_pipeline.py:"
        "run_financial_monitor_daily_pipeline"
    ) in prefect_yaml
    assert "pull" not in prefect_config
    assert deployment["work_pool"]["name"] == "windows-process-pool"
    assert "config_path" not in deployment["parameters"]
    assert deployment["pull"] == [
        {
            "prefect.deployments.steps.set_working_directory": {
                "directory": "/opt/prefect/prefect_marimo_starter"
            }
        }
    ]


def test_docs_reference_financial_monitor_workflow():
    readme_text = Path("README.md").read_text(encoding="utf-8")
    adding_flows_text = Path("docs/ADDING_FLOWS.md").read_text(encoding="utf-8")
    setup_doc = Path("docs/financial_monitor/financial_monitor_setup.md").read_text(
        encoding="utf-8"
    )

    assert "financial monitor" in readme_text.lower()
    assert "notebooks/financial_monitor/financial_monitor_daily_pipeline.py" in adding_flows_text
    assert "windows-process-pool" in setup_doc
    assert "EDINET" in setup_doc
    assert "TDnet" in setup_doc


def test_repo_contains_local_prefect_compose_setup():
    compose_text = Path("docker-compose.yaml").read_text(encoding="utf-8")
    dockerfile_text = Path("Dockerfile.prefect-dev").read_text(encoding="utf-8")
    env_example = Path(".env.example").read_text(encoding="utf-8")
    setup_doc = Path("docs/financial_monitor/financial_monitor_setup.md").read_text(
        encoding="utf-8"
    )
    prefect_dev_doc = Path("docs/prefect/prefect_local_dev_stack.md").read_text(
        encoding="utf-8"
    )
    readme_text = Path("README.md").read_text(encoding="utf-8")

    assert "prefecthq/prefect" in dockerfile_text
    assert "prefect-worker:" in compose_text
    assert "4201:4200" in compose_text
    assert "shared_utils.prefect_postgres" in compose_text
    assert "PREFECT_API_DATABASE_CONNECTION_URL" in compose_text
    assert "PREFECT_SERVER_DATABASE_SQLALCHEMY_CONNECT_ARGS_SEARCH_PATH" in compose_text
    assert "prefect work-pool create windows-process-pool --type process" in compose_text
    assert "source: ${PROJECT_ROOT" in compose_text
    assert "target: /opt/prefect/prefect_marimo_starter" in compose_text
    assert "working_dir: /opt/prefect/prefect_marimo_starter" in compose_text
    assert "./data/prefect_home" not in compose_text
    assert "docker compose up -d" in setup_doc
    assert "PREFECT_API_DATABASE_CONNECTION_URL=postgresql+asyncpg://" in env_example
    assert (
        "PREFECT_SERVER_DATABASE_SQLALCHEMY_CONNECT_ARGS_SEARCH_PATH="
        "prefect_marimo_starter,public"
    ) in env_example
    assert "PROJECT_ROOT" in setup_doc
    assert "PROJECT_ROOT=/absolute/path/to/prefect_marimo_starter" in env_example
    assert "host.docker.internal" in setup_doc
    assert "docs/prefect/prefect_local_dev_stack.md" in readme_text
    assert "prefect_local_dev_stack.md" in setup_doc
    assert "set_working_directory" in prefect_dev_doc
    assert "/opt/prefect/prefect_marimo_starter" in prefect_dev_doc
    assert "repo root" in prefect_dev_doc.lower()
    assert "host.docker.internal" in prefect_dev_doc
    assert "financial-monitor-daily-prod" in prefect_dev_doc
    assert "docker compose up -d" in prefect_dev_doc
    assert "same PostgreSQL database" in prefect_dev_doc
    assert "unique schema" in prefect_dev_doc
    assert "Repo A" in prefect_dev_doc
    assert "Repo B" in prefect_dev_doc
    assert "different database name" in prefect_dev_doc
    assert "public" in prefect_dev_doc
    assert "do not pin config_path" in prefect_dev_doc
