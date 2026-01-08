# CLI Reference

Overview: Commands available via `winsw` or the renamed wrapper executable. Most commands require Administrator privileges.

## Core commands

- `install [config] [options]`: Install service from XML.
- `uninstall [config]`: Uninstall service.
- `start [config]`: Start the service.
- `stop [--force] [config]`: Stop the service (optionally force).
- `restart [--force] [config]`: Restart the service.
- `status [config]`: Print service status.
- `refresh [config]`: Refresh service properties without reinstall.
- `customize`: Customize the wrapper executable branding/metadata.

## Dev commands (experimental)

- `dev ps`: Show process tree for the service.
- `dev kill`: Kill a stuck service.
- `dev list`: List services managed by current executable.

## Notes

- Use bundled mode (`myapp.exe`) to omit config path when the XML is co-located and name-matched.
- UAC prompts in non-elevated sessions.

## References

- CLI commands doc: https://github.com/winsw/winsw/blob/v3/docs/cli-commands.md
- README usage: https://github.com/winsw/winsw/blob/v3/README.md
