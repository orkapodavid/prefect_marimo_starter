"""
Deployment script for the daily data sync workflow.
"""
import sys
import os

# Ensure project root is in path
sys.path.append(os.getcwd())

from notebooks.etl.daily_data_sync import run_daily_sync
from src.shared_utils.config import get_settings

def deploy():
    settings = get_settings()
    work_pool_name = settings.work_pool_name if hasattr(settings, "work_pool_name") else "local-subprocess"

    print(f"Deploying flow to work pool: {work_pool_name}")

    # Define the deployment
    deployment_id = run_daily_sync.from_source(
        source=".",
        entrypoint="notebooks/etl/daily_data_sync.py:run_daily_sync"
    ).deploy(
        name="exchange-powered-flow",
        work_pool_name=work_pool_name,
        cron="0 9 * * *",
        tags=["etl", "daily"],
        description="Daily data sync with Exchange notifications on failure."
    )

    print(f"Deployment created with ID: {deployment_id}")

if __name__ == "__main__":
    deploy()
