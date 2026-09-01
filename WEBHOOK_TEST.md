# Webhook Testing Tool

Interactive Python script for manual testing of the Deskly webhook ingestion endpoint.

## Requirements

```bash
pip install requests python-dotenv
```

## Setup

1. Ensure the Deskly API is running (http://localhost:8000)
2. Optionally set `API_URL` in your `.env` (defaults to `http://localhost:8000`)

```bash
# .env (at project root, optional)
API_URL=http://localhost:8000
```

When running the script, you will be prompted to enter:
- `Webhook Secret` — the HMAC-SHA256 secret for your test
- `Event ID` — unique identifier for the webhook event
- `Title` — ticket title (max 200 chars)
- `Description` — ticket description
- `Priority` — select from menu (baja, media, alta, urgente)

**Note:** `WEBHOOK_SECRET` is NOT read from `.env`. You input it interactively when testing.

## Usage

```bash
python test_webhook.py
```

An interactive menu appears with the following options:

```
Main Menu
1) Send webhook (manual input)
2) Send webhook (from example)
3) Test invalid signature (should return 401)
4) Test malformed payload (should return 422)
5) Test idempotency (same event_id twice)
6) Exit
```

## Features

### Option 1: Send Webhook (Manual Input)
You input all required fields:
- **Webhook Secret** (required): The HMAC secret used to sign the request
- **Event ID** (required): Unique identifier (e.g., `inc-001`, `sf-123`)
- **Title** (required, max 200 chars): The ticket title
- **Description** (required): The ticket description
- **Priority** (selector): Choose from `baja`, `media`, `alta`, `urgente`
- **Assignee ID** (optional): User ID or leave blank

Then the script:
- Computes HMAC-SHA256 signature automatically
- Sends the request with proper headers
- Displays the response in real-time

### Option 2: Send Webhook (From Example)
- Choose a provider example (Inc, Salesforce, Jira, Custom)
- Input the Webhook Secret
- Optionally edit other fields
- Send and inspect response

### 3. Test Invalid Signature
- You input all payload fields (manual input required)
- Script sends with deliberately wrong signature
- Expected response: **401 Unauthorized**

### 4. Test Malformed Payload
- You input the Webhook Secret
- Script sends a payload missing the required `titulo` field
- Expected response: **422 Unprocessable Entity**

### 5. Test Idempotency
- You input all payload fields (manual input required)
- Script sends the same request twice automatically
- Observe: First → 201 (created), Second → 200 (idempotent duplicate)

### Workflow Examples

#### Workflow 1: Quick Test with Manual Input
```
$ python test_webhook.py
Select option: 1

Webhook Secret: my-secret-key-123
Event ID: inc-001
Title: Database connection failed
Description: The API cannot connect to PostgreSQL
Priority:
  1) baja
  2) media
  3) alta
  4) urgente
Select (1-4): 4
Assignee ID: [press Enter]

[Request sent, response displayed]
✓ Webhook accepted! Ticket created.
```

#### Workflow 2: Test from Example
```
Select option: 2
Available examples:
  1) Inc
  2) Salesforce
  3) Jira
  4) Custom
Select example: 1
Webhook Secret: change-me
Edit payload? (y/n): n

[Request sent, response displayed]
```

#### Workflow 3: Security Testing
```
Select option: 3  # Invalid signature test
Webhook Secret: my-secret
Event ID: test-001
...
[Sends with wrong signature]
Status Code: 401
✓ Correctly rejected invalid signature (401)

Select option: 4  # Malformed payload test
Webhook Secret: my-secret
[Sends payload without titulo field]
Status Code: 422
✓ Correctly rejected malformed payload (422)
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

**Note:** `WEBHOOK_SECRET` is provided interactively in the script, not from `.env`.

## Exit

Press Ctrl+C or select option 6 to exit gracefully.
