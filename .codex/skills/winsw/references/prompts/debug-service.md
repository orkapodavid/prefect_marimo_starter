# Prompt: Debug Service Configuration

Goal: Diagnose misconfigurations causing startup/stop issues.

## Steps
- Verify required fields and paths
- Check working directory and `%BASE%`
- Inspect stop behavior: `stoptimeout`, `stoparguments`
- Review logs and stdout/stderr redirection
- Evaluate service account permissions

## Expected output
- List of issues with line references
- Suggested fixes referencing [CONFIGURATION.md](../CONFIGURATION.md)
