# Prefect Flow Notification System — Implementation Spec

**Date**: 2026-03-23  
**Status**: Draft  

---

## 1. What We Want

A notification system for **Prefect 3.0** flows that:

1. Sends **rich HTML emails** (via Microsoft Exchange / EWS) when flows fail, succeed, or crash
2. Sends **Symphony bot messages** (via REST API) to chat rooms
3. Routes notifications to **different channels per flow tag** (e.g., `asx` flows → ASX Symphony room + email, `etl` → email only)
4. Is **reliable** — retries on transient failures, degrades gracefully if one channel is down

---

## 2. Components to Build

### 2.1 Exchange Email Channel

| Aspect | Detail |
|--------|--------|
| Library | `exchangelib` (Python EWS client) |
| Auth | Username + password, optional explicit EWS URL (otherwise autodiscover) |
| Content | **HTML email** using `exchangelib.HTMLBody` |
| Subject | `[{env}] ❌ flow-name — Failed` or `✅ Succeeded` or `💥 Crashed` |
| Body includes | Flow name, run name, state, Prefect UI link (`{api_url}/flow-runs/{run_id}`), parameters, traceback (failures), timestamp in `Asia/Hong_Kong` |
| Recipients | Comma-separated list from config, overridable per tag |

### 2.2 Symphony Bot Channel

| Aspect | Detail |
|--------|--------|
| Protocol | REST — POST `/agent/v4/stream/{streamId}/message/create` |
| Auth | Bot RSA JWT (sign with private key) **or** session token — confirm with infra team |
| Content | [MessageML](https://docs.developers.symphony.com/building-bots-on-symphony/messages/overview-of-messageml) card with flow name, state, timestamp, Prefect link |
| Target | Stream ID (room ID) from config, overridable per tag |

### 2.3 Notification Router

Decides which channels + targets to use based on Prefect flow **tags**:

```yaml
# config/notification_routes.yaml
routes:
  asx:
    - channel: symphony
      target: "ASX_STREAM_ID_HERE"
    - channel: email
      target: "asx-team@company.com"
  tdnet:
    - channel: symphony
      target: "JAPAN_STREAM_ID_HERE"
    - channel: email
      target: "japan-team@company.com"
  etl:
    - channel: email
      target: "ops@company.com"
  "*":   # default fallback
    - channel: email
      target: "admin@company.com"
```

### 2.4 Prefect Hooks

Three hook functions that attach to `@flow`:

```python
@flow(
    name="my-flow",
    on_failure=[notify_on_failure],
    on_completion=[notify_on_success],
    on_crashed=[notify_on_crash],
)
def my_flow():
    ...
```

Each hook calls the router, which fans out to the configured channels.

---

## 3. Configuration

All settings via environment variables (or `.env` file). Use Pydantic `BaseSettings` or equivalent.

### Email settings

```env
NOTIFICATION_ENABLED=true
NOTIFICATION_EMAIL=admin@example.com
NOTIFY_ON_FAILURE=true
NOTIFY_ON_SUCCESS=false
EXCHANGE_USERNAME=user@company.com
EXCHANGE_PASSWORD=secret
EXCHANGE_EWS_URL=https://mail.company.com/EWS/Exchange.asmx
```

### Symphony settings

```env
SYMPHONY_BOT_ENABLED=false
SYMPHONY_POD_URL=https://corporate.symphony.com
SYMPHONY_SESSION_AUTH_URL=https://corporate-api.symphony.com/sessionauth
SYMPHONY_KEY_AUTH_URL=https://corporate-api.symphony.com/keyauth
SYMPHONY_AGENT_URL=https://corporate-api.symphony.com/agent
SYMPHONY_BOT_USERNAME=prefect-bot
SYMPHONY_BOT_PRIVATE_KEY_PATH=/path/to/bot-private-key.pem
SYMPHONY_DEFAULT_STREAM_ID=abc123streamid
```

### General

```env
ENVIRONMENT=dev
PREFECT_API_URL=http://localhost:4200/api
NOTIFICATION_ROUTES_FILE=config/notification_routes.yaml
```

---

## 4. Reliability Requirements

| Requirement | Implementation |
|-------------|---------------|
| Retry | 3 attempts, exponential backoff (1s → 2s → 4s) per channel |
| Graceful degradation | If Symphony fails, still send email (and vice versa) |
| Logging | Structured: channel, recipient/stream, flow_run_id, attempt #, success/fail |
| Connection reuse | Cache Exchange connection (don't create a new one per notification) |

---

## 5. Suggested File Layout

```
src/
├── services/
│   ├── exchange_email/
│   │   └── exchange_email_service.py   # EWS client (send_email with HTML support)
│   └── symphony/
│       └── symphony_bot_service.py     # Symphony REST client (auth + send message)
└── shared_utils/
    ├── config.py                       # Pydantic settings with all env vars above
    ├── prefect_notifications.py        # Hook functions (on_failure/success/crash)
    └── prefect_notification_router.py  # Tag → channel routing + message building
```

---

## 6. Acceptance Criteria

- [ ] Flow failure → HTML email with Prefect run link + traceback
- [ ] Flow success → HTML email (when `NOTIFY_ON_SUCCESS=true`)
- [ ] Flow crash → notification via crash hook
- [ ] Symphony bot sends MessageML card to configured room
- [ ] Tag-based routing works (tag match → correct channels, fallback to `*`)
- [ ] One channel down → other channels still fire
- [ ] Unit tests pass (mock all external calls)

---

## 7. Testing

- **Unit tests only** — mock `exchangelib` and Symphony HTTP calls
- Test routing logic: tag matching, wildcard fallback, multi-channel dispatch
- Test message building: HTML email content, MessageML content
- Test retry logic: simulate transient failures, verify backoff behaviour

---

## 8. Dependencies

```
exchangelib          # EWS client for Exchange email
requests             # Symphony REST calls
cryptography         # RSA JWT signing for Symphony bot auth
pyyaml               # Routing config file
pydantic-settings    # Config management
```

> If `symphony-bdk-python` is available, use it instead of raw `requests` + `cryptography`.
