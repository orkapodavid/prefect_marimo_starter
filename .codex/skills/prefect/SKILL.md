---
name: Prefect
description: This skill should be used when the user asks to "create a prefect flow", "add prefect task", "deploy prefect workflow", "configure prefect.yaml", "set up work pool", "use prefect blocks", or mentions Prefect orchestration, flow scheduling, or task retries.
version: 0.1.0
---

# Prefect

Prefect is a workflow orchestration framework for Python that enables building, scheduling, and monitoring data pipelines with features like retries, caching, and distributed execution.

## Core Concepts

**Flows**: The main unit of orchestration. A flow is a container for workflow logic decorated with `@flow`:

```python
from prefect import flow

@flow(name="my-flow", log_prints=True)
def my_flow(param: str) -> dict:
    print(f"Running with {param}")
    return {"status": "success"}
```

**Tasks**: Atomic units of work within flows. Tasks can be retried, cached, and configured independently:

```python
from prefect import task

@task(retries=3, retry_delay_seconds=30, cache_key_fn=task_input_hash)
def my_task(data: dict) -> dict:
    return process(data)
```

**Key Features**:
- Automatic retry logic for transient failures
- Task result caching based on inputs
- Distributed execution across work pools
- Observable execution with logging and state tracking

## Deployment Patterns

Define deployments in `prefect.yaml` to schedule and configure flows:

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

**Key Configuration**:
- `entrypoint` - Path to flow function (module:function)
- `work_pool` - Target work pool for execution
- `schedules` - Cron expressions or interval-based schedules
- `parameters` - Default parameter values for the flow

## Work Pools

Work pools determine where and how flows execute:

- **Process**: Local Python subprocess (Windows compatible, no containers)
- **Docker**: Container-based execution with image management
- **Kubernetes**: Kubernetes Job-based execution for cloud deployments
- **Managed**: Prefect Cloud-managed infrastructure

Start a worker to execute flows from a pool:

```bash
prefect worker start --pool my-pool --type process
```

## Blocks

Blocks provide secure configuration and secret management:

```python
from prefect.blocks.system import Secret, JSON

# Load secrets
db_url = Secret.load("database-url").get()

# Load configuration
config = JSON.load("app-config").value
```

Create blocks via UI or CLI to store credentials, connection strings, and configuration without hardcoding sensitive values.

## CLI Reference

| Command | Purpose |
|---------|---------|
| `prefect server start` | Start self-hosted Prefect server |
| `prefect worker start --pool <name> --type process` | Start worker for specified pool |
| `prefect deploy --all` | Deploy all flows defined in prefect.yaml |
| `prefect deployment run <name>` | Trigger deployment manually |

## Additional Resources

### Reference Files

For detailed configuration options and advanced patterns, consult:
- **`references/api-reference.md`** - Detailed task configuration, deployment patterns, work pool specifications, block types, and full documentation links
