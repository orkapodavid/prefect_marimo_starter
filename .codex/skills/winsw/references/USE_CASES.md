# Use Cases & Patterns

Overview: Typical scenarios where WinSW excels.

## Web applications

- Host ASP.NET, .NET, Node.js, or Python web servers as services.
- Use `<startarguments>` for app DLL or script; configure logs and stop behavior.

## Background jobs

- Run schedulers, workers, or daemons; use failure actions to auto-restart.

## Data processing

- ETL pipelines; ensure working directory and env vars for dependencies.

## Monitoring & alerting

- Wrap agents that produce health logs; use rotation and stderr redirection.

## Multi-instance deployment

- Use different `<id>` and config files for multiple instances; parameterize paths.

## CI/CD integration

- Package service with app; use customize command; manage via scripts.

## References

- Samples: https://github.com/winsw/winsw/blob/v3/samples
- Deferred file operations: https://github.com/winsw/winsw/blob/v3/docs/deferred-file-operations.md
