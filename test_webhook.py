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
        "asignado_a_id": None,
    }


def example_salesforce() -> dict[str, Any]:
    """Example event from Salesforce."""
    return {
        "event_id": f"sf-{int(time.time() * 1000)}",
        "titulo": "Customer complaint: Login issues",
        "descripcion": "Account SF-00Q1234567 reports persistent login failures since 10:30 UTC.",
        "prioridad": "alta",
        "asignado_a_id": None,
    }


def example_jira() -> dict[str, Any]:
    """Example event from Jira."""
    return {
        "event_id": f"jira-PROJ-{int(time.time())}",
        "titulo": "PROJ-1234: Fix API rate limiting",
        "descripcion": "The API rate limiter is incorrectly rejecting valid requests. Root cause: misconfigured Redis TTL.",
        "prioridad": "media",
        "asignado_a_id": None,
    }


def example_custom() -> dict[str, Any]:
    """Placeholder for custom event."""
    return {
        "event_id": "custom-001",
        "titulo": "Custom event",
        "descripcion": "Edit this example to match your needs.",
        "prioridad": "media",
        "asignado_a_id": None,
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


def edit_json_in_place(data: dict[str, Any]) -> dict[str, Any]:
    """Allow user to edit the JSON payload interactively."""
    print("\nCurrent payload:")
    print(json.dumps(data, indent=2))
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
            else:
                data[field] = user_input

    return data


def send_webhook(
    api_url: str, webhook_secret: str, payload: dict[str, Any], include_timestamp: bool = False
) -> None:
    """Send webhook and display response."""
    print_header("Sending Webhook")

    # Serialize payload
    body = json.dumps(payload, separators=(",", ":")).encode()
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
    print(json.dumps(payload, indent=2))

    # Send request
    print("\nSending...\n")
    try:
        response = requests.post(
            f"{api_url}/api/webhooks/tickets",
            json=payload,
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

    body = json.dumps(payload, separators=(",", ":")).encode()
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
            json=payload,
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
            json=bad_payload,
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


def test_idempotency(api_url: str, webhook_secret: str, payload: dict[str, Any]) -> None:
    """Test webhook idempotency with same event_id."""
    print_header("Testing Idempotency (Same event_id)")

    print_info("Sending the same event_id twice. The second should return the existing ticket.\n")

    # First request
    print("📨 First request:")
    send_webhook(api_url, webhook_secret, payload, include_timestamp=False)

    print("\n" + "="*70)
    print("Waiting 2 seconds before second request...\n")
    time.sleep(2)

    # Second request (same event_id)
    print("📨 Second request (same event_id):")
    send_webhook(api_url, webhook_secret, payload, include_timestamp=False)


def main() -> None:
    """Main interactive loop."""
    config = load_env_config()
    api_url = config["api_url"]
    webhook_secret = config["webhook_secret"]

    print_header("Deskly Webhook Testing Tool")
    print_info(f"API URL: {api_url}")
    print_info(f"Webhook Secret: {webhook_secret[:10]}...")

    while True:
        print("\n" + "="*70)
        print("Main Menu")
        print("="*70)
        print("\n1) Send webhook (choose example or custom)")
        print("2) Test invalid signature (should return 401)")
        print("3) Test malformed payload (should return 422)")
        print("4) Test idempotency (same event_id twice)")
        print("5) Exit")

        choice = input("\nSelect option (1-5): ").strip()

        if choice == "1":
            show_examples()
            example_choice = input("\nSelect example (1-4): ").strip()
            payload = get_example_data(example_choice)

            if payload is None:
                print_error("Invalid choice")
                continue

            edit = input("Edit payload? (y/n) [n]: ").strip().lower()
            if edit == "y":
                payload = edit_json_in_place(payload)

            send_webhook(api_url, webhook_secret, payload, include_timestamp=True)

        elif choice == "2":
            show_examples()
            example_choice = input("\nSelect example (1-4): ").strip()
            payload = get_example_data(example_choice)

            if payload is None:
                print_error("Invalid choice")
                continue

            test_invalid_signature(api_url, payload)

        elif choice == "3":
            test_malformed_payload(api_url, webhook_secret)

        elif choice == "4":
            show_examples()
            example_choice = input("\nSelect example (1-4): ").strip()
            payload = get_example_data(example_choice)

            if payload is None:
                print_error("Invalid choice")
                continue

            test_idempotency(api_url, webhook_secret, payload)

        elif choice == "5":
            print("\nGoodbye!")
            break

        else:
            print_error("Invalid option. Please select 1-5.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(0)
