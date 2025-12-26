# .codex/skills/prefect.md

## Prefect 3.x Skill

### Core Concepts

**Flows**: The main unit of orchestration
```python
from prefect import flow

@flow(name="my-flow", log_prints=True)
def my_flow(param: str) -> dict:
    print(f"Running with {param}")
    return {"status": "success"}
```

**Tasks**: Atomic units of work within flows
```python
from prefect import task

@task(retries=3, retry_delay_seconds=30, cache_key_fn=task_input_hash)
def my_task(data: dict) -> dict:
    return process(data)
```

### Deployment Patterns

**prefect.yaml structure**:
```yaml
name: my-project
prefect-version: "3.0"

deployments:
  - name: my-deployment
    entrypoint: flows/main.py:main_flow
    work_pool:
      name: my-pool
      work_queue_name: default
    schedules:
      - cron: "0 6 * * *"
        timezone: "UTC"
```

### Work Pools

- **Process**: Local Python subprocess (Windows compatible)
- **Docker**: Container-based execution
- **Kubernetes**: K8s Job-based execution
- **Managed**: Prefect Cloud infrastructure

### Blocks

```python
from prefect.blocks.system import Secret, JSON

# Load secrets
db_url = Secret.load("database-url").get()

# Load configuration
config = JSON.load("app-config").value
```

### CLI Reference

| Command | Purpose |
|---------|---------|
| `prefect server start` | Start self-hosted server |
| `prefect worker start --pool <name> --type process` | Start worker |
| `prefect deploy --all` | Deploy all flows |
| `prefect deployment run <name>` | Trigger deployment |

### Key Documentation Links

- Flows: https://docs.prefect.io/v3/concepts/flows
- Tasks: https://docs.prefect.io/v3/concepts/tasks
- Deployments: https://docs.prefect.io/v3/concepts/deployments
- Work Pools: https://docs.prefect.io/v3/concepts/work-pools
- Workers: https://docs.prefect.io/v3/concepts/workers
