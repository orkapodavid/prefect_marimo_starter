# Troubleshooting

Overview: Common issues, diagnostics, and resolutions for WinSW services.

## Service fails to stop gracefully

- Ensure `<stoptimeout>` is sufficient.
- Provide `<stoparguments>` and optionally `<stopexecutable>` for graceful shutdown.
- For GUI apps, ensure close messages are handled.

## Logs not appearing

- Check `<logpath>` and `<log mode>`.
- Redirect streams via `stdoutPath`/`stderrPath`.

## Encoding issues in console output

- Use versions supporting UTF-8 code page; verify environment.

## Shared drive not available

- Configure `<sharedDirectoryMapping>`; ensure domain policies allow mapping.

## Permissions/UAC prompts

- Run commands elevated; verify `securityDescriptor` and account rights.

## CLI not finding config

- In global mode, pass `myapp.xml` path; in bundled mode, ensure name match and co-location.

## References

- Logging & error reporting: https://github.com/winsw/winsw/blob/v3/docs/logging-and-error-reporting.md
- XML config examples: https://github.com/winsw/winsw/blob/v3/samples
