# Prompt: Design a Windows Service with WinSW

Goal: Plan and produce a WinSW configuration for a new application.

## Inputs to consider
- Executable path and arguments; working directory
- Stop strategy and timeout; hooks needed
- Logging strategy and rotation; stdout/stderr
- Service account and permissions; security descriptor
- Failure actions and auto-restart policy
- Shared directories or downloads

## Output
- Rationale bullets for each design choice
- Final XML config
- Deployment checklist referencing [deployment-checklist.md](../TEMPLATES/deployment-checklist.md)
