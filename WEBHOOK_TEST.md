# Webhook Testing Tool

Interactive Python script for manual testing of the Deskly webhook ingestion endpoint.

## Requirements

```bash
pip install requests python-dotenv
```

## Setup

1. Ensure the Deskly API is running (http://localhost:8000)
2. Check your `.env` file for `API_URL` and `WEBHOOK_SECRET`

```bash
# .env (at project root)
API_URL=http://localhost:8000
WEBHOOK_SECRET=change-me
```

If not set, defaults are:
- `API_URL=http://localhost:8000`
- `WEBHOOK_SECRET=change-me`

## Usage

```bash
python test_webhook.py
```

## Features

### 1. Send Webhook
- **Choose a provider example**: Inc, Salesforce, Jira, or Custom
- **Edit payload**: Customize event_id, titulo, descripcion, prioridad, asignado_a_id
- **Automatic signature generation**: HMAC-SHA256 computed and injected
- **Timestamp support**: Optional X-Timestamp header for replay protection testing
- **Live response inspection**: See status code, headers, and parsed JSON response

### 2. Test Invalid Signature
Sends a request with a deliberately wrong signature:
- Expected response: **401 Unauthorized**
- Verifies that signature validation happens before payload processing

### 3. Test Malformed Payload
Sends a request missing the required `titulo` field:
- Expected response: **422 Unprocessable Entity**
- Verifies that payload validation rejects incomplete data

### 4. Test Idempotency
Sends the same event_id twice:
- First request: Should create ticket (201)
- Second request: Should return existing ticket (200)
- Demonstrates idempotency protection against retries

## Example Workflows

### Workflow 1: Quick Manual Test
```
1. Select "Send webhook (choose example or custom)"
2. Choose "1 (Inc)"
3. Press Enter to skip editing
4. Watch response appear in real-time
```

### Workflow 2: Integration Test with Custom Data
```
1. Select "Send webhook"
2. Choose "4 (Custom)"
3. Edit payload to match your test case
4. Send and inspect response
```

### Workflow 3: Security Testing
```
1. Select "Test invalid signature"
2. Verify API rejects with 401
3. Select "Test malformed payload"
4. Verify API rejects with 422
```

### Workflow 4: Idempotency Verification
```
1. Select "Test idempotency"
2. Choose a provider
3. Tool sends same event_id twice automatically
4. Observe both responses (first creates, second returns existing)
```

## Provider Examples

### Inc (Incident Management)
- event_id: `inc-1725091623` (Unix timestamp based)
- Common for on-call/incident systems

### Salesforce
- event_id: `sf-00Q1234567` (Salesforce object ID)
- Typical SaaS CRM webhook format

### Jira
- event_id: `jira-PROJ-1725091623` (Project + timestamp)
- Atlassian ecosystem integration

### Custom
- Placeholder for your own event_id convention
- Edit all fields to match your test case

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_URL` | `http://localhost:8000` | Base URL of Deskly API |
| `WEBHOOK_SECRET` | `change-me` | HMAC-SHA256 secret (must match API's `WEBHOOK_SECRET`) |

## Exit

Press Ctrl+C or select option 5 to exit gracefully.
