# Prompt: Generate WinSW Config

Goal: Given service specs, output a valid WinSW XML configuration.

## Instructions
- Use `<service>` root with required `<id>` and `<executable>`
- Prefer `%BASE%` for local paths
- Include `<log mode>`; add hooks and failure actions when specified
- Validate against [CONFIGURATION.md](../CONFIGURATION.md)

## Input format
```
name: MyApp
id: myapp
executable: %BASE%\myExecutable.exe
startarguments: --port 8080
stoptimeout: 30 sec
onfailure:
  - action: restart
    delay: 10 sec
```

## Output format (XML)
```xml
<service>
  <id>myapp</id>
  <executable>%BASE%\myExecutable.exe</executable>
  <startarguments>--port 8080</startarguments>
  <stoptimeout>30 sec</stoptimeout>
  <onfailure action="restart" delay="10 sec"/>
  <log mode="roll"/>
</service>
```
