# MCP Server Setup Guide

This guide explains how to set up Model Context Protocol (MCP) servers for this project. This configuration allows AI assistants (like Claude Desktop or other MCP-compliant tools) to interact with Prefect and Marimo directly.

## Configuration Overview

You typically add these configurations to your MCP client's configuration file (e.g., `claude_desktop_config.json` for Claude Desktop).

### 1. Prefect MCP Server

The Prefect MCP server allows the AI to inspect flows, deployments, and runs. It is run as a **command-based** server.

We recommend using `uvx` (part of the `uv` package manager) to run the server without installing it globally.

**Configuration:**

```json
"prefect": {
    "command": "/path/to/uvx",
    "args": [
        "--from",
        "prefect-mcp",
        "prefect-mcp-server"
    ]
}
```

> **Note:** You normally need to provide the **absolute path** to the `uvx` executable in the `command` field. You can find this by running `which uvx` in your terminal.
> Example: `/Users/username/.local/bin/uvx`

### 2. Marimo MCP Server

The Marimo MCP server allows the AI to edit and interact with notebooks. Marimo runs as a local web server, so the MCP configuration connects to it via a **URL** (SSE).

**Prerequisites:**
1.  Start your Marimo server (e.g., `marimo edit` or `marimo run`).
2.  Note the URL and Access Token provided in the terminal output.

**Configuration:**

```json
"marimo": {
    "serverUrl": "http://localhost:2718/mcp/server?access_token=YOUR_ACCESS_TOKEN"
}
```

> **Important:** The `access_token` is required for security. Copy it from your running Marimo instance's logs.

## Complete Example

Here is a complete example configuration combining both servers. Replace paths and tokens with your actual values.

```json
{
    "mcpServers": {
        "prefect": {
            "command": "/Users/davidor/.local/bin/uvx",
            "args": [
                "--from",
                "prefect-mcp",
                "prefect-mcp-server"
            ]
        },
        "marimo": {
            "serverUrl": "http://localhost:2718/mcp/server?access_token=Zmhkrgbg6HxYw8h93GSR3w"
        }
    }
}
```

### Installation Pointers

- **Prefect MCP**: No manual installation needed if you use `uvx`. It downloads `prefect-mcp` on demand.
- **Marimo MCP**: Built into Marimo. Ensure you have the latest version of `marimo` installed in your environment.
