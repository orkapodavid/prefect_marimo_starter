---
name: Windows Service Wrapper (WinSW)
description: This skill should be used when the user asks to "install a service", "configure winsw", "troubleshoot windows service wrapper", "create a windows service wrapper config", "manage windows services", or needs help with managing Windows services using WinSW.
version: 0.1.0
---

# Windows Service Wrapper (WinSW)

This skill provides guidance for using **WinSW (Windows Service Wrapper)**, a tool that wraps any executable as a Windows Service. It allows you to start, stop, and monitor applications (like Java jars, Python scripts, Node.js apps, or any executable) using standard Windows Service commands.

## When to Use This Skill

Use this skill to:
1.  **Wrap an executable** as a Windows Service.
2.  **Generate configuration** (XML) for WinSW.
3.  **Install, start, stop, or uninstall** services managed by WinSW.
4.  **Troubleshoot** service failures, log rotation, or permissions.

## Usage Overview

### 1. Installation

To set up a service:
1.  Download the latest `WinSW-x64.exe` (or appropriate version) from GitHub releases.
2.  Rename it to your service name, e.g., `myapp.exe`.
3.  Create an XML configuration file next to it named `myapp.xml`.

### 2. Configuration

The core of WinSW is the XML configuration file.

**Minimal Example (`examples/minimal.xml`):**
```xml
<service>
  <id>myapp</id>
  <name>My App Service</name>
  <description>Runs My App as a service.</description>
  <executable>node.exe</executable>
  <arguments>server.js</arguments>
</service>
```

**Common Elements:**
*   `<id>`: Unique service ID (no spaces).
*   `<name>`: Display name in Windows Services.
*   `<description>`: Description.
*   `<executable>`: Program to run.
*   `<arguments>`: Arguments for the program.
*   `<log>`: Log configuration (mode, directory, etc.).
*   `<env>`: Environment variables.

For a complete reference, see **`references/CONFIGURATION.md`**.

### 3. Management Commands

Run these commands in a terminal (Admin required for install/uninstall):

*   **Install:** `myapp.exe install`
*   **Start:** `myapp.exe start`
*   **Stop:** `myapp.exe stop`
*   **Restart:** `myapp.exe restart`
*   **Status:** `myapp.exe status`
*   **Uninstall:** `myapp.exe uninstall`

For CLI details, see **`references/CLI_REFERENCE.md`**.

## Additional Resources

### Reference Files
*   **`references/CONFIGURATION.md`**: Complete XML configuration guide.
*   **`references/CLI_REFERENCE.md`**: Command-line options.
*   **`references/TROUBLESHOOTING.md`**: Solutions for common errors.
*   **`references/FEATURE.md`**: Advanced features like specific accounts, delayed start, etc.

### Examples
*   **`examples/minimal.xml`**: A simple starting point.
*   **`examples/template.xml`**: A robust template with logging and error handling.

### Scripts
*   **`scripts/validate-winsw-config.ps1`**: PowerShell script to validate your XML config.

### Assets
*   **`assets/winsw_config_schema.json`**: JSON Schema for validation.

## Best Practices
*   **Always use absolute paths** in `<executable>` if the PATH environment variable is not reliable.
*   **Configure logging** (`<log>`) to rotate files and prevent disk fill-up.
*   **Use `<onfailure>`** to define restart behavior.
*   **Test manually** by running the executable directly in a console before wrapping it as a service.
