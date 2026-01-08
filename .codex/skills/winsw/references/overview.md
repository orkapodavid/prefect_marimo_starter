# WinSW Agent Skill

Overview of Windows Service Wrapper (WinSW): a permissively licensed tool to run any executable as a Windows Service. This skill provides LLM-ready documentation, examples, templates, and prompts to design, configure, and troubleshoot WinSW services.

- Official repo: https://github.com/winsw/winsw
- License: MIT
- Supported platforms: WinSW 3 runs on Windows with .NET Framework 4.6.1+ or as native x86/x64 based on .NET 7; WinSW 2.x binaries available via GitHub Releases and NuGet.

## Quick start

1. Download WinSW from GitHub Releases: https://github.com/winsw/winsw/releases
2. Create `myapp.xml` next to `WinSW.exe` (or rename to `myapp.exe`).
3. Install service: `winsw install myapp.xml [options]` or `myapp.exe install [options]`
4. Start service: `winsw start myapp.xml` or `myapp.exe start`
5. Check status: `winsw status myapp.xml`

See [CONFIGURATION.md](CONFIGURATION.md) and [CLI_REFERENCE.md](CLI_REFERENCE.md).

## Contents

- ARCHITECTURE.md – Internals & SCM interaction
- INSTALLATION_SETUP.md – Prereqs, download, install
- CONFIGURATION.md – Complete XML configuration reference
- CLI_REFERENCE.md – Commands and options
- FEATURES.md – Capabilities and advanced settings
- SECURITY.md – Security guidance and service accounts
- TROUBLESHOOTING.md – Common issues and resolutions
- USE_CASES.md – Practical scenarios and patterns
- EXAMPLES/ – Ready-to-use XML samples
- TEMPLATES/ – Generic template and checklists
- PROMPTS/ – LLM prompts for config, debug, troubleshoot, design
- QUICK_REFERENCE.md – One-page cheat sheet
- INDEX.md – Cross-references
- winsw_config_template.json – JSON mirror of XML (for LLM spec)
- winsw_config_schema.json – JSON Schema (non-official) for validation
- Scripts/validate-winsw-config.ps1 – PowerShell XML validator

## References

- Repo homepage: https://github.com/winsw/winsw (README, platform support, usage)
- Docs index: https://github.com/winsw/winsw/tree/v3/docs
- XML spec: https://github.com/winsw/winsw/blob/v3/docs/xml-config-file.md
- CLI commands: https://github.com/winsw/winsw/blob/v3/docs/cli-commands.md
- Samples: https://github.com/winsw/winsw/blob/v3/samples
- License: https://github.com/winsw/winsw/blob/v3/LICENSE.txt
