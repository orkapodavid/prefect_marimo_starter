# Installation & Setup

Overview: Install WinSW as a global or bundled tool. Ensure platform prerequisites.

## Prerequisites

- Windows 10/11 or Windows Server (Core) 2012 R2+.
- For WinSW 3: .NET Framework 4.6.1+ or use native x86/x64 executables built on .NET 7.
- Administrator privileges for service operations (UAC elevation).

## Download sources

- GitHub Releases (latest/pre-releases): https://github.com/winsw/winsw/releases
- NuGet (WinSW 2.x): https://www.nuget.org/packages/WinSW/
- Jenkins Maven packaging (2.x binaries): https://repo.jenkins-ci.org/releases/com/sun/winsw/winsw/

## Global tool usage

1. Take `WinSW.exe` or `WinSW.zip` from distribution.
2. Write `myapp.xml` (see XML spec and samples).
3. Install: `winsw install myapp.xml [options]`
4. Start: `winsw start myapp.xml`
5. Status: `winsw status myapp.xml`

## Bundled tool usage

1. Rename `WinSW.exe` to your app name, e.g., `myapp.exe`.
2. Place `myapp.exe` and `myapp.xml` side by side.
3. Install: `myapp.exe install [options]`
4. Start: `myapp.exe start`

## Service account options

- Default: LocalSystem.
- Use `<serviceaccount>` to run under LocalService, NetworkService, or a user account.
- Optionally enable `<allowservicelogon>true</allowservicelogon>`.

## References

- README: https://github.com/winsw/winsw/blob/v3/README.md
- XML spec: https://github.com/winsw/winsw/blob/v3/docs/xml-config-file.md
- CLI commands: https://github.com/winsw/winsw/blob/v3/docs/cli-commands.md
