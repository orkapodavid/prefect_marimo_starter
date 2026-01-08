# Architecture: WinSW Internals

Overview: WinSW is a wrapper executable that installs and manages a target application as a Windows Service, bridging between Windows Service Control Manager (SCM) and the managed process.

## Core components and flow

- Wrapper executable (`WinSW.exe` or renamed): hosts the service and exposes CLI commands.
- Configuration file (`<service>` XML): controls identity, execution, shutdown, logging, accounts, and extras.
- SCM interaction: install/start/stop/restart/status via Service APIs; failure actions configured with `<onfailure>`.
- Stop behavior: attempts graceful stop by sending Ctrl+C (console) or Close message (GUI), waits up to `stoptimeout` (default 15s), then terminates.
- Working directory: default is the folder containing the XML config; relative paths resolved from it.
- Environment: `BASE` env var set to wrapper folder; `<env>` defines additional variables.

## Logging and monitoring

- Log path and mode: `<logpath>` and `<log mode="append|reset|ignore|roll">`.
- Error reporting: see docs/logging-and-error-reporting.md.
- UTF-8 console output code page supported (v2.11+), stdout/stderr redirection via `stdoutPath`/`stderrPath`.

## Extensions and advanced hooks

- Pre/Post hooks: `<prestart>`, `<poststart>`, `<prestop>`, `<poststop>` with executable and arguments.
- Preshutdown: `<preshutdown>` and `<preshutdownTimeout>` give extra time during system shutdown.
- Shared directory mapping: `<sharedDirectoryMapping>` maps UNC paths to drive letters before start.
- Auto refresh: `<autoRefresh>` updates service properties on start/stop/restart.

## Service accounts and security

- Default account: LocalSystem.
- Alternatives: LocalService, NetworkService, or user (`<serviceaccount>` with `<username>`, `<password>`, `<allowservicelogon>`).
- UPN support, credential prompting via `<prompt>` or CLI options.
- Security descriptor: `securityDescriptor` (SDDL) for service ACLs.

## Version line

- WinSW 2.x: mature line; latest stable tag v2.12.0.
- WinSW 3.x: actively developed alpha; .NET 7 native builds; breaking changes and new CLI.

## References

- README: https://github.com/winsw/winsw/blob/v3/README.md
- XML spec: https://github.com/winsw/winsw/blob/v3/docs/xml-config-file.md
- CLI: https://github.com/winsw/winsw/blob/v3/docs/cli-commands.md
- Logging: https://github.com/winsw/winsw/blob/v3/docs/logging-and-error-reporting.md
