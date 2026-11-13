"""Submit an application to HowGood's signed application API.

Usage:
    python3 submit.py application.json          # validate and print the body; nothing is sent
    python3 submit.py application.json --send   # prompt for the signing key, then send

The signing key comes from the HowGood instructions page. It is read with
getpass, so it is not stored in this file or in the shell history.
"""

from __future__ import annotations

import argparse
import getpass
import hmac
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ENDPOINT = "https://howgood-apply-api.howgood.workers.dev/apply"
USER_AGENT = "howgood-apply/1.0"
TIMEOUT_SECONDS = 15

REQUIRED = ("name", "email", "resume", "location", "linkedin", "codeLink")
OPTIONAL_INT = ("yearsPython", "yearsDjango")
OPTIONAL_STR = ("repos", "notes")
URL_FIELDS = ("resume", "linkedin", "codeLink", "repos")
ALLOWED = set(REQUIRED) | set(OPTIONAL_INT) | set(OPTIONAL_STR)


def validate_payload(payload: object) -> list[str]:
    """Return a list of problems. An empty list means the payload is valid."""
    if not isinstance(payload, dict):
        return ["Payload must be a JSON object."]

    errors = []
    unknown = set(payload) - ALLOWED
    if unknown:
        errors.append(f"Unknown fields: {', '.join(sorted(unknown))}")

    for field in REQUIRED:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field} must be a non-empty string.")

    for field in OPTIONAL_STR:
        if field in payload and not isinstance(payload[field], str):
            errors.append(f"{field} must be a string.")

    # bool is a subclass of int, so check the exact type.
    for field in OPTIONAL_INT:
        if field in payload and (type(payload[field]) is not int or payload[field] < 0):
            errors.append(f"{field} must be a non-negative integer.")

    for field in URL_FIELDS:
        value = payload.get(field)
        if isinstance(value, str) and value.strip() and not value.startswith("https://"):
            errors.append(f"{field} must start with https://.")

    return errors


def encode_body(payload: dict) -> bytes:
    """Serialize the payload once. These exact bytes are signed and sent."""
    return json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def sign(body: bytes, secret: bytes) -> str:
    """Return the hex-encoded HMAC-SHA256 of the raw request body."""
    return hmac.new(secret, body, "sha256").hexdigest()


def send(body: bytes, signature: str) -> tuple[int, str]:
    """POST the signed body. Returns (status, response text)."""
    request = Request(
        ENDPOINT,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-HMAC-Signature": signature,
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Submit a HowGood application.")
    parser.add_argument("payload", type=Path, help="JSON file with the application fields")
    parser.add_argument("--send", action="store_true", help="actually send the POST")
    args = parser.parse_args(argv)

    try:
        payload = json.loads(args.payload.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        parser.error(f"Could not read payload: {exc}")

    errors = validate_payload(payload)
    if errors:
        parser.error("\n  " + "\n  ".join(errors))

    body = encode_body(payload)

    if not args.send:
        print("Payload is valid. This body would be sent (nothing was sent):")
        print(body.decode("utf-8"))
        return 0

    secret = getpass.getpass("HowGood signing key: ").encode("utf-8")
    if not secret:
        parser.error("Signing key cannot be empty.")

    try:
        status, text = send(body, sign(body, secret))
    except (URLError, TimeoutError) as exc:
        # The request may have reached the server. Resending could create a duplicate.
        print(f"No confirmation received: {exc}. Check before retrying.")
        return 1

    print(f"HTTP {status}: {text}")
    return 0 if status == 201 else 1


if __name__ == "__main__":
    raise SystemExit(main())
