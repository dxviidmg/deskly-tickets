#!/usr/bin/env python3
"""
Interactive webhook testing script for Deskly.

Allows manual testing of the webhook ingestion endpoint with:
- Custom or predefined event data
- Automatic HMAC-SHA256 signature generation
- Multiple provider examples (Inc, Salesforce, Jira)
- Real-time response inspection

Usage:
  python test_webhook.py
"""
import hashlib
import hmac
import json
import os
import sys
import time
from typing import Any

import requests
from dotenv import load_dotenv


def load_env_config() -> dict[str, str]:
    """Load configuration from .env or use defaults."""
    load_dotenv()
    return {
        "api_url": os.getenv("API_URL", "http://localhost:8000"),
        "webhook_secret": os.getenv("WEBHOOK_SECRET", "change-me"),
    }


def compute_signature(body: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature of the body."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def print_success(msg: str) -> None:
    """Print a success message in green."""
    print(f"✓ {msg}")


def print_error(msg: str) -> None:
    """Print an error message in red."""
    print(f"✗ {msg}")


def print_info(msg: str) -> None:
    """Print an info message."""
    print(f"ℹ {msg}")


def example_inc() -> dict[str, Any]:
    """Example event from Inc (incident management system)."""
    return {
        "event_id": f"inc-{int(time.time())}",
        "titulo": "Critical: Database connection timeout",
        "descripcion": "The application cannot connect to the primary database. Failover to replica in progress.",
        "prioridad": "urgente",
    }


def example_salesforce() -> dict[str, Any]:
    """Example event from Salesforce."""
    return {
        "event_id": f"sf-{int(time.time() * 1000)}",
        "titulo": "Customer complaint: Login issues",
        "descripcion": "Account SF-00Q1234567 reports persistent login failures since 10:30 UTC.",
        "prioridad": "alta",
    }


def example_jira() -> dict[str, Any]:
    """Example event from Jira."""
    return {
        "event_id": f"jira-PROJ-{int(time.time())}",
        "titulo": "PROJ-1234: Fix API rate limiting",
        "descripcion": "The API rate limiter is incorrectly rejecting valid requests. Root cause: misconfigured Redis TTL.",
        "prioridad": "media",
    }


def example_custom() -> dict[str, Any]:
    """Placeholder for custom event."""
    return {
        "event_id": "custom-001",
        "titulo": "Custom event",
        "descripcion": "Edit this example to match your needs.",
        "prioridad": "media",
    }


def show_examples() -> None:
    """Display all example providers."""
    examples = {
        "1": ("Inc", example_inc),
        "2": ("Salesforce", example_salesforce),
        "3": ("Jira", example_jira),
        "4": ("Custom", example_custom),
    }
    print("\nAvailable examples:")
    for key, (name, _) in examples.items():
        print(f"  {key}) {name}")


def get_example_data(choice: str) -> dict[str, Any] | None:
    """Get example data by choice."""
    examples = {
        "1": example_inc,
        "2": example_salesforce,
        "3": example_jira,
        "4": example_custom,
    }
    if choice in examples:
        return examples[choice]()
    return None


def select_prioridad() -> str:
    """Interactive selector for priority level."""
    prioridades = ["baja", "media", "alta", "urgente"]
    print("\nSelect priority:")
    for i, p in enumerate(prioridades, 1):
        print(f"  {i}) {p}")
    
    while True:
        choice = input("Select (1-4): ").strip()
        if choice in ["1", "2", "3", "4"]:
            return prioridades[int(choice) - 1]
        print_error("Invalid choice. Please select 1-4.")


def get_simple_payload(webhook_secret: str) -> dict[str, Any]:
    """Quick payload: only ask for title and description, use predefined values for others."""
    print("\n" + "="*70)
    print("  Quick Webhook Test (using .env WEBHOOK_SECRET)")
    print("="*70 + "\n")
    
    # Event ID (auto-generated)
    event_id = f"test-{int(time.time())}"
    print(f"Event ID (auto-generated): {event_id}")
    
    # Title
    titulo = input("Title (required, max 200 chars): ").strip()
    if not titulo or len(titulo) > 200:
        print_error("Title must be 1-200 characters")
        return get_simple_payload(webhook_secret)
    
    # Description
    descripcion = input("Description (required): ").strip()
    if not descripcion:
        print_error("Description cannot be empty")
        return get_simple_payload(webhook_secret)
    
    # Priority (default to media)
    prioridad = "media"
    print(f"Priority (default): {prioridad}")
    
    return {
        "event_id": event_id,
        "titulo": titulo,
        "descripcion": descripcion,
        "prioridad": prioridad,
        "_webhook_secret": webhook_secret,
    }


def get_manual_payload() -> dict[str, Any]:
    """Get payload by asking user for all required fields."""
    print("\n" + "="*70)
    print("  Enter Webhook Payload")
    print("="*70 + "\n")
    
    # Webhook Secret
    webhook_secret = input("Webhook Secret (required): ").strip()
    if not webhook_secret:
        print_error("Webhook secret cannot be empty")
        return get_manual_payload()
    
    # Event ID
    event_id = input("Event ID (required, e.g., 'inc-001', 'sf-123'): ").strip()
    if not event_id or len(event_id) > 120:
        print_error("Event ID must be 1-120 characters")
        return get_manual_payload()
    
    # Title
    titulo = input("Title (required, max 200 chars): ").strip()
    if not titulo or len(titulo) > 200:
        print_error("Title must be 1-200 characters")
        return get_manual_payload()
    
    # Description
    descripcion = input("Description (required): ").strip()
    if not descripcion:
        print_error("Description cannot be empty")
        return get_manual_payload()
    
    # Priority (selector)
    prioridad = select_prioridad()
    
    return {
        "event_id": event_id,
        "titulo": titulo,
        "descripcion": descripcion,
        "prioridad": prioridad,
        "_webhook_secret": webhook_secret,  # Store for later use
    }


def edit_json_in_place(data: dict[str, Any]) -> dict[str, Any]:
    """Allow user to edit the JSON payload interactively."""
    print("\nCurrent payload:")
    display_data = {k: v for k, v in data.items() if k != "_webhook_secret"}
    print(json.dumps(display_data, indent=2))
    print("\nEdit fields (or press Enter to skip):")

    fields = ["event_id", "titulo", "descripcion", "prioridad", "asignado_a_id"]
    for field in fields:
        current = data[field]
        user_input = input(f"  {field} [{current}]: ").strip()
        if user_input:
            if field == "asignado_a_id":
                try:
                    data[field] = int(user_input) if user_input.lower() != "none" else None
                except ValueError:
                    data[field] = None
                    print_error(f"Invalid integer for {field}, set to None")
            elif field == "prioridad":
                if user_input in ["baja", "media", "alta", "urgente"]:
                    data[field] = user_input
                else:
                    print_error(f"Invalid priority. Must be one of: baja, media, alta, urgente")
            else:
                data[field] = user_input

    return data


def send_webhook(
    api_url: str, payload: dict[str, Any], include_timestamp: bool = False
) -> None:
    """Send webhook and display response."""
    print_header("Sending Webhook")

    # Make a copy to avoid modifying the original
    payload_copy = payload.copy()
    
    # Extract webhook_secret from payload
    webhook_secret = payload_copy.pop("_webhook_secret", "change-me")
    
    # Serialize payload (without the webhook_secret)
    body = json.dumps(payload_copy, separators=(",", ":")).encode()
    signature = compute_signature(body, webhook_secret)

    # Prepare headers
    headers = {
        "Content-Type": "application/json",
        "X-Signature": signature,
    }
    if include_timestamp:
        headers["X-Timestamp"] = str(time.time())

    # Display request details
    print_info(f"POST {api_url}/api/webhooks/tickets")
    print("\nHeaders:")
    for key, value in headers.items():
        if key == "X-Signature":
            print(f"  {key}: {value[:20]}...")
        else:
            print(f"  {key}: {value}")
    print("\nPayload:")
    print(json.dumps(payload_copy, indent=2))

    # Send request
    print("\nSending...\n")
    try:
        # Send the exact bytes that were signed (`body`). Using `json=` would
        # let requests re-serialize the payload with different separators,
        # producing a body that no longer matches the signature (-> 401).
        response = requests.post(
            f"{api_url}/api/webhooks/tickets",
            data=body,
            headers=headers,
            timeout=10,
        )

        # Display response
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        print("\nResponse Body:")
        try:
            print(json.dumps(response.json(), indent=2))
        except Exception:
            print(response.text)

        if response.status_code == 201:
            print_success("Webhook accepted! Ticket created.")
        elif response.status_code == 200:
            print_info("Webhook accepted (idempotent duplicate).")
        else:
            print_error(f"Webhook rejected with status {response.status_code}")

    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")


def test_invalid_signature(api_url: str, payload: dict[str, Any]) -> None:
    """Test webhook with invalid signature."""
    print_header("Testing Invalid Signature")

    # Remove webhook_secret from display
    payload_copy = {k: v for k, v in payload.items() if k != "_webhook_secret"}
    
    body = json.dumps(payload_copy, separators=(",", ":")).encode()
    headers = {
        "Content-Type": "application/json",
        "X-Signature": "invalid-signature-xyz",
    }

    print_info(f"POST {api_url}/api/webhooks/tickets")
    print("Headers:")
    print(f"  X-Signature: invalid-signature-xyz")
    print("\nSending request with invalid signature...\n")

    try:
        response = requests.post(
            f"{api_url}/api/webhooks/tickets",
            data=body,
            headers=headers,
            timeout=10,
        )
        print(f"Status Code: {response.status_code}")
        print(json.dumps(response.json(), indent=2))

        if response.status_code == 401:
            print_success("Correctly rejected invalid signature (401)")
        else:
            print_error(f"Expected 401, got {response.status_code}")

    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")


def test_malformed_payload(api_url: str, webhook_secret: str) -> None:
    """Test webhook with malformed payload."""
    print_header("Testing Malformed Payload")

    # Missing required field (titulo)
    bad_payload = {
        "event_id": "test-malformed",
        "descripcion": "Missing titulo field",
        "prioridad": "media",
    }

    body = json.dumps(bad_payload, separators=(",", ":")).encode()
    signature = compute_signature(body, webhook_secret)
    headers = {
        "Content-Type": "application/json",
        "X-Signature": signature,
    }

    print_info(f"POST {api_url}/api/webhooks/tickets")
    print("Payload (missing 'titulo'):")
    print(json.dumps(bad_payload, indent=2))
    print("\nSending request with malformed payload...\n")

    try:
        response = requests.post(
            f"{api_url}/api/webhooks/tickets",
            data=body,
            headers=headers,
            timeout=10,
        )
        print(f"Status Code: {response.status_code}")
        print(json.dumps(response.json(), indent=2))

        if response.status_code == 422:
            print_success("Correctly rejected malformed payload (422)")
        else:
            print_error(f"Expected 422, got {response.status_code}")

    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")


def test_idempotency(api_url: str, payload: dict[str, Any]) -> None:
    """Test webhook idempotency with same event_id."""
    print_header("Testing Idempotency (Same event_id)")

    print_info("Sending the same event_id twice. The second should return the existing ticket.\n")

    # First request
    print("📨 First request:")
    send_webhook(api_url, payload.copy(), include_timestamp=False)

    print("\n" + "="*70)
    print("Waiting 2 seconds before second request...\n")
    time.sleep(2)

    # Second request (same event_id)
    print("📨 Second request (same event_id):")
    send_webhook(api_url, payload.copy(), include_timestamp=False)


def main() -> None:
    """Main interactive loop."""
    config = load_env_config()
    api_url = config["api_url"]
    webhook_secret = config["webhook_secret"]

    print_header("Deskly Webhook Testing Tool")
    print_info(f"API URL: {api_url}")
    print_info(f"Webhook Secret from .env: {webhook_secret[:10]}...")

    while True:
        print("\n" + "="*70)
        print("Main Menu")
        print("="*70)
        print("\n1) Quick test (uses .env WEBHOOK_SECRET, only ask title + description)")
        print("2) Send webhook (manual input - ask for everything)")
        print("3) Send webhook (from example)")
        print("4) Test invalid signature (should return 401)")
        print("5) Test malformed payload (should return 422)")
        print("6) Test idempotency (same event_id twice)")
        print("7) Exit")

        choice = input("\nSelect option (1-7): ").strip()

        if choice == "1":
            # Quick test: only ask for titulo and descripcion
            payload = get_simple_payload(webhook_secret)
            send_webhook(api_url, payload, include_timestamp=True)

        elif choice == "2":
            # Manual input for all fields
            payload = get_manual_payload()
            send_webhook(api_url, payload, include_timestamp=True)

        elif choice == "3":
            # Choose from examples and edit
            show_examples()
            example_choice = input("\nSelect example (1-4): ").strip()
            payload = get_example_data(example_choice)

            if payload is None:
                print_error("Invalid choice")
                continue

            # Ask for webhook_secret
            webhook_secret_input = input("\nWebhook Secret (required): ").strip()
            if not webhook_secret_input:
                print_error("Webhook secret cannot be empty")
                continue
            
            payload["_webhook_secret"] = webhook_secret_input

            edit = input("Edit payload? (y/n) [n]: ").strip().lower()
            if edit == "y":
                payload = edit_json_in_place(payload)

            send_webhook(api_url, payload, include_timestamp=True)

        elif choice == "4":
            # Test invalid signature
            payload = get_manual_payload()
            test_invalid_signature(api_url, payload)

        elif choice == "5":
            # Test malformed payload
            webhook_secret_input = input("Webhook Secret (required): ").strip()
            if not webhook_secret_input:
                print_error("Webhook secret cannot be empty")
                continue
            test_malformed_payload(api_url, webhook_secret_input)

        elif choice == "6":
            # Test idempotency
            payload = get_manual_payload()
            test_idempotency(api_url, payload)

        elif choice == "7":
            print("\nGoodbye!")
            break

        else:
            print_error("Invalid option. Please select 1-7.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(0)
