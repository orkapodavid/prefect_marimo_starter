# Configuration Validation Rules

- Required: `<id>`, `<executable>`
- If `<stoparguments>` present, use `<startarguments>`; optionally `<stopexecutable>`
- `stoptimeout` must be a positive duration (sec/min/hour/day)
- `priority` ∈ {idle, belownormal, normal, abovenormal, high, realtime}
- `<serviceaccount>`: if `<username>` ends with `$`, omit password (gMSA)
- `<sharedDirectoryMapping>`: each `<map>` needs `label` and `uncpath`
- `<onfailure>`: `action` ∈ {restart, reboot, none}; optional `delay`
