# Configuration (XML) Reference

Overview: WinSW configuration is an XML file rooted at `<service>` that controls service identity, execution, stop behavior, logging, failure actions, environment, accounts, and advanced features.

## Structure and required elements

- `<service>`: root element.
- Required: `<id>`, `<executable>`.
- Optional: `<name>`, `<description>`, `<startmode>` (Automatic|Manual), `<delayedAutoStart>` (bool).

## Execution & arguments

- `<arguments>`: inline string or multiline child text; use `<startarguments>` when `<stoparguments>` is set.
- `<workingdirectory>`: default is folder containing XML.
- `<priority>`: idle|belownormal|normal|abovenormal|high|realtime.
- `<hidewindow>`: true|false.

## Stop behavior

- `<stoptimeout>`: duration (e.g., `15 sec`), default 15s.
- `<stoparguments>` and `<stopexecutable>`: run custom stop program/args.

## Logging

- `<logpath>`: directory for logs.
- `<log mode="append|reset|ignore|roll">`.
- `stdoutPath` / `stderrPath` in hook commands to redirect streams.

## Failure actions

- `<onfailure action="restart|reboot|none" delay="10 sec">` repeatable.
- `<resetfailure>`: duration to reset failure count, default 1 day.

## Environment

- `<env name="VAR" value="..."/>`; `BASE` is pre-set to wrapper directory.

## Security & accounts

- `<serviceaccount>`: `<username>`, optional `<password>`, `<allowservicelogon>`, `<prompt>`.
- `securityDescriptor`: SDDL string for service ACLs.

## Advanced hooks

- `<prestart>`, `<poststart>`, `<prestop>`, `<poststop>` each supports `<executable>`, `<arguments>`, `stdoutPath`, `stderrPath`.
- `<preshutdown>` and `<preshutdownTimeout>`.
- `<autoRefresh>`: default true.
- `<sharedDirectoryMapping>` with `<map label="N:" uncpath="\\UNC"/>` entries.

## Example (minimal)

```xml
<service>
  <id>myapp</id>
  <executable>%BASE%\myExecutable.exe</executable>
  <log mode="roll"/>
</service>
```

## Example (stop arguments)

```xml
<service>
  <id>webapp</id>
  <executable>dotnet</executable>
  <startarguments>MyWeb.dll</startarguments>
  <stopexecutable>dotnet</stopexecutable>
  <stoparguments>MyWeb.dll --stop</stoparguments>
  <stoptimeout>30 sec</stoptimeout>
</service>
```

## References

- XML spec (authoritative): https://github.com/winsw/winsw/blob/v3/docs/xml-config-file.md
- Complete sample: https://github.com/winsw/winsw/blob/v3/samples/complete.xml
- Samples dir: https://github.com/winsw/winsw/blob/v3/samples
