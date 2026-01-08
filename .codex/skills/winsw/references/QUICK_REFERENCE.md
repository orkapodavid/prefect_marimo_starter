# Quick Reference

## Essential steps
- Place `WinSW.exe` and `myapp.xml` together (or rename to `myapp.exe`)
- Install: `winsw install myapp.xml` or `myapp.exe install`
- Start: `winsw start myapp.xml` or `myapp.exe start`
- Status: `winsw status myapp.xml`

## Required XML
- `<id>` unique service ID
- `<executable>` path or command

## Common options
- `<stoptimeout>15 sec</stoptimeout>`
- `<log mode="roll"/>`
- Failure actions: `<onfailure action="restart" delay="10 sec"/>`
- Service account: `<serviceaccount><username>NT AUTHORITY\LocalService</username></serviceaccount>`

## Docs
- Config spec: docs/xml-config-file.md
- CLI: docs/cli-commands.md
- Samples: /samples
