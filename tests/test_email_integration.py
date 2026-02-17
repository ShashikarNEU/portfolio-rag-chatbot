"""
Live integration test — sends a REAL email via the running server.

Prerequisites:
  1. Server running:  uv run uvicorn app.main:app --reload
  2. Real API keys in .env (OPENAI_API_KEY, SENDGRID_API_KEY, etc.)

Run:
  uv run pytest tests/test_email_integration.py -s
"""

import httpx
import pytest

BASE_URL = "http://localhost:8000/api/v1"


@pytest.mark.integration
def test_send_email_tool() -> None:
    """POST a message with name/email/inquiry and verify email_sent is True."""
    payload = {
        "message": (
            "I'd like to get in touch. "
            "My name is Mark Test, "
            "my email is marktest@gmail.com, "
            "and my inquiry is: This is an automated integration test email."
        ),
    }

    with httpx.Client(timeout=60) as client:
        resp = client.post(f"{BASE_URL}/chat", json=payload)

    assert resp.status_code == 200, f"Unexpected status {resp.status_code}: {resp.text}"

    data = resp.json()
    assert data["email_sent"] is True, f"email_sent was False. Response: {data['response']}"
    print(f"\n✅ Email sent! Response: {data['response']}")
