# Features

Overview: Key capabilities provided by WinSW for robust Windows services.

## Service management

- Install/uninstall/start/stop/restart/status/refresh.
- Auto refresh of service properties.

## Startup & shutdown control

- Graceful stop signals (Ctrl+C for console, Close message for GUI).
- `stoptimeout` for graceful shutdown window; force terminate beyond timeout.

## Hooks & tasks

- Pre/Post start/stop hooks to run auxiliary commands.
- Deferred file operations and downloads before start.

## Logging

- Log rotation modes; stdout/stderr redirection; improved exception logging; UTF-8 code page.

## Reliability

- Failure actions via `<onfailure>`; self-restarting services pattern.

## Environment & working directory

- `BASE` var; `<env>` entries; default working directory = XML folder.

## Accounts & security

- Run as LocalSystem/LocalService/NetworkService/user; credential prompting; SDDL descriptor.

## Shared directory mapper

- Map UNC paths to drive letters for services that need network shares.

## References

- Docs: https://github.com/winsw/winsw/tree/v3/docs
- Self-restarting: https://github.com/winsw/winsw/blob/v3/docs/self-restarting-service.md
- Deferred ops: https://github.com/winsw/winsw/blob/v3/docs/deferred-file-operations.md
