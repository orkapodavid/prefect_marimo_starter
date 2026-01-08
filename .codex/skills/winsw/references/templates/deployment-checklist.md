# Deployment Checklist

- [ ] Verify platform prerequisites (.NET Framework 4.6.1+ or native .NET 7 build)
- [ ] Place `WinSW.exe` (or renamed) and XML config side by side
- [ ] Use `%BASE%` for co-located assets
- [ ] Confirm service account permissions (least privilege)
- [ ] Validate `stoptimeout` and graceful stop path
- [ ] Configure logs (path, mode, stdout/stderr)
- [ ] Set failure actions and reset window
- [ ] Test hooks (pre/post start/stop)
- [ ] Map shared directories if needed
- [ ] Run install/start/status with elevation
