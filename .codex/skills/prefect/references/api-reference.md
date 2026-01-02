# Prefect API Reference

This document provides detailed configuration options, advanced patterns, and comprehensive documentation for Prefect 3.x.

## Task Configuration Options

### Retry Configuration

```python
from prefect import task
from prefect.tasks import task_input_hash

@task(
    retries=3,                      # Number of retry attempts
    retry_delay_seconds=30,         # Delay between retries
    retry_jitter_factor=0.5,        # Add randomness to retry delay
    retry_condition_fn=lambda task, task_run, state: state.is_failed()
)
def resilient_task():
    pass
```

**Retry Strategies**:
- `retry_delay_seconds` - Fixed delay
- `retry_jitter_factor` - Random jitter to prevent thundering herd
- `retry_condition_fn` - Custom logic to determine if retry should occur

### Caching

```python
from datetime import timedelta
from prefect.tasks import task_input_hash

@task(
    cache_key_fn=task_input_hash,           # Cache based on inputs
    cache_expiration=timedelta(hours=1)     # Cache lifetime
)
def expensive_computation(x: int) -> int:
    return x ** 2

# Custom cache key
def custom_cache_key(context, parameters):
    return f"{parameters['x']}-{context.flow_run.id}"

@task(cache_key_fn=custom_cache_key)
def custom_cached_task(x: int):
    pass
```

**Cache Key Functions**:
- `task_input_hash` - Hash of input parameters (default)
- `None` - Disable caching
- Custom function - Implement custom caching logic

### Concurrency

```python
@task(
    task_run_name="process-{item}",  # Dynamic task run names
    timeout_seconds=300,              # Task timeout
    log_prints=True                   # Capture print statements
)
def process_item(item: str):
    print(f"Processing {item}")

# Concurrency limits
from prefect import task, flow
from prefect.concurrency.sync import concurrency

@task
def limited_task():
    with concurrency("database-access", occupy=1):
        # Only N tasks can execute this block simultaneously
        query_database()
```

### Result Configuration

```python
from prefect import task
from prefect.results import ResultRecord

@task(
    persist_result=True,              # Store result for retrieval
    result_storage="s3-bucket-block", # Where to store results
    result_serializer="json"          # How to serialize results
)
def task_with_results():
    return {"status": "complete"}
```

## Flow Configuration Options

### Flow Metadata

```python
from prefect import flow

@flow(
    name="my-etl-pipeline",           # Display name in UI
    description="ETL pipeline for customer data",
    version="1.2.0",                  # Flow version
    flow_run_name="etl-{date}",       # Dynamic run names
    log_prints=True,                  # Capture print statements
    timeout_seconds=3600,             # Flow timeout
    validate_parameters=True          # Validate input parameters
)
def etl_flow(date: str):
    pass
```

### Subflows

```python
@flow
def subflow(x: int) -> int:
    return x * 2

@flow
def main_flow():
    # Subflows run within parent flow context
    result = subflow(5)
    return result
```

### Flow Return Values

```python
@flow
def flow_with_return() -> dict:
    # Return value is tracked as flow state result
    return {
        "status": "success",
        "records_processed": 1000,
        "duration_seconds": 45.2
    }
```

## Advanced Deployment Patterns

### Multiple Deployments

```yaml
deployments:
  - name: daily-sync-dev
    entrypoint: notebooks/etl/sync.py:sync_flow
    work_pool:
      name: dev-pool
    parameters:
      environment: "dev"
      batch_size: 100
    schedules:
      - cron: "0 8 * * *"
        timezone: "UTC"
  
  - name: daily-sync-prod
    entrypoint: notebooks/etl/sync.py:sync_flow
    work_pool:
      name: prod-pool
    parameters:
      environment: "prod"
      batch_size: 1000
    schedules:
      - cron: "0 6 * * *"
        timezone: "Asia/Hong_Kong"
```

### Parameterized Schedules

```yaml
deployments:
  - name: hourly-report
    entrypoint: notebooks/reports/report.py:generate_report
    parameters:
      report_type: "summary"
    schedules:
      # Every hour during business hours
      - cron: "0 9-17 * * 1-5"
        timezone: "America/New_York"
      
      # Weekly summary on Monday morning
      - cron: "0 8 * * 1"
        timezone: "America/New_York"
        parameters:
          report_type: "weekly"
```

### Build Steps

```yaml
build:
  - prefect.deployments.steps.run_shell_script:
      script: scripts/build.sh
      stream_output: true
  
  - prefect.deployments.steps.pip_install_requirements:
      requirements_file: requirements.txt

push:
  - prefect_docker.deployments.steps.build_docker_image:
      image_name: my-flow
      tag: latest
```

## Work Pool Specifications

### Process Pool

```bash
# Create process pool
prefect work-pool create my-pool --type process

# Start worker
prefect worker start --pool my-pool --type process
```

**Configuration**:
```yaml
work_pool:
  name: windows-process-pool
  work_queue_name: default
  job_variables:
    env:
      PYTHONPATH: "/app/src"
      LOG_LEVEL: "INFO"
```

### Docker Pool

```bash
# Create Docker pool
prefect work-pool create docker-pool --type docker

# Worker configuration
prefect worker start --pool docker-pool --type docker
```

**Configuration**:
```yaml
work_pool:
  name: docker-pool
  job_variables:
    image: "my-registry/my-flow:latest"
    env:
      DATABASE_URL: "{{ prefect.blocks.secret.db-url }}"
    volumes:
      - "/data:/app/data:ro"
    network_mode: "bridge"
```

### Kubernetes Pool

```yaml
work_pool:
  name: k8s-pool
  job_variables:
    image: "my-flow:latest"
    namespace: "prefect"
    service_account_name: "prefect-worker"
    image_pull_policy: "Always"
    resources:
      requests:
        memory: "512Mi"
        cpu: "500m"
      limits:
        memory: "1Gi"
        cpu: "1000m"
```

## Block Types and Usage

### Secret Block

```python
from prefect.blocks.system import Secret

# Create via code
secret = Secret(value="my-secret-value")
secret.save("my-secret", overwrite=True)

# Load and use
api_key = Secret.load("api-key").get()
```

### JSON Block

```python
from prefect.blocks.system import JSON

# Create configuration block
config = JSON(value={
    "database": {
        "host": "localhost",
        "port": 5432
    },
    "api_endpoint": "https://api.example.com"
})
config.save("app-config", overwrite=True)

# Load configuration
cfg = JSON.load("app-config").value
db_host = cfg["database"]["host"]
```

### String Block

```python
from prefect.blocks.system import String

# Simple string storage
connection_string = String(value="Server=localhost;Database=mydb")
connection_string.save("db-connection", overwrite=True)

# Load
conn_str = String.load("db-connection").value
```

### DateTime Block

```python
from prefect.blocks.system import DateTime
from datetime import datetime

# Store timestamp
last_run = DateTime(value=datetime.now())
last_run.save("last-sync-time", overwrite=True)

# Load
last_sync = DateTime.load("last-sync-time").value
```

### Custom Blocks

```python
from prefect.blocks.core import Block
from pydantic import Field

class DatabaseConfig(Block):
    host: str = Field(description="Database host")
    port: int = Field(default=5432, description="Database port")
    database: str = Field(description="Database name")
    
    def get_connection_string(self) -> str:
        return f"postgresql://{self.host}:{self.port}/{self.database}"

# Register block type
DatabaseConfig.register_type_and_schema()

# Create and save
db_config = DatabaseConfig(
    host="prod-db.example.com",
    port=5432,
    database="analytics"
)
db_config.save("prod-database", overwrite=True)

# Load and use
config = DatabaseConfig.load("prod-database")
conn_str = config.get_connection_string()
```

## Advanced Task Patterns

### Task Dependencies

```python
from prefect import flow, task

@task
def task_a():
    return "A"

@task
def task_b():
    return "B"

@task
def task_c(a_result, b_result):
    return f"{a_result} + {b_result}"

@flow
def parallel_flow():
    # Tasks A and B run in parallel
    result_a = task_a()
    result_b = task_b()
    
    # Task C waits for both
    result_c = task_c(result_a, result_b)
    return result_c
```

### Map Task

```python
@task
def process_item(item: str) -> str:
    return item.upper()

@flow
def batch_flow(items: list[str]):
    # Process items in parallel
    results = process_item.map(items)
    return results

# Usage
batch_flow(["a", "b", "c", "d"])
```

### Task with State

```python
from prefect import task, get_run_logger
from prefect.states import Failed

@task
def conditional_task(x: int):
    logger = get_run_logger()
    
    if x < 0:
        logger.warning("Negative value detected")
        return Failed(message="Negative value not allowed")
    
    return x * 2
```

## Documentation Links

- **Prefect Docs**: https://docs.prefect.io/v3/
- **Flows**: https://docs.prefect.io/v3/concepts/flows
- **Tasks**: https://docs.prefect.io/v3/concepts/tasks
- **Deployments**: https://docs.prefect.io/v3/concepts/deployments
- **Work Pools**: https://docs.prefect.io/v3/concepts/work-pools
- **Workers**: https://docs.prefect.io/v3/concepts/workers
- **Blocks**: https://docs.prefect.io/v3/concepts/blocks
- **Results**: https://docs.prefect.io/v3/concepts/results
- **API Reference**: https://docs.prefect.io/v3/api-ref/
- **GitHub**: https://github.com/PrefectHQ/prefect
- **Community**: https://discourse.prefect.io/
