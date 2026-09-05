#!/usr/bin/env python3
"""
Google Drive OAuth 2.0 Authorization (non-interactive, for headless servers).

Usage:
    # Step 1: Generate auth URL
    python gdrive_auth_helper.py url

    # Step 2: Open URL in browser, authorize, get code from redirect
    # Step 3: Exchange code for token
    python gdrive_auth_helper.py exchange "YOUR_CODE"

    # Verify existing token
    python gdrive_auth_helper.py verify
"""

import json
import os
import sys
import hashlib
import secrets
import base64

CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "credentials.json")
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "token.json")

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# This redirect_uri must match what's registered in Google Cloud Console
# For OOB flow (copy-paste), use urn:ietf:wg:oauth:2.0:oob
# For localhost redirect, use http://localhost:8080
REDIRECT_URI = "http://localhost:8080"


def _load_client_config():
    """Load client_id and client_secret from credentials.json."""
    with open(CREDENTIALS_FILE) as f:
        config = json.load(f)
    web = config.get("web", config.get("installed", {}))
    return web["client_id"], web["client_secret"]


def generate_url():
    """Generate OAuth authorization URL."""
    client_id, _ = _load_client_config()

    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
    }

    url = "https://accounts.google.com/o/oauth2/auth?" + "&".join(
        f"{k}={v}" for k, v in params.items()
    )
    print(url)
    return url


def exchange_code(code: str):
    """Exchange authorization code for token using raw HTTP."""
    import urllib.request

    client_id, client_secret = _load_client_config()

    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    encoded = "&".join(f"{k}={v}" for k, v in data.items()).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=encoded,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(req) as resp:
            tokens = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"ERROR: {e.code} - {error_body}")
        sys.exit(1)

    token_data = {
        "token": tokens.get("access_token"),
        "refresh_token": tokens.get("refresh_token"),
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": client_id,
        "client_secret": client_secret,
        "scopes": SCOPES,
    }

    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    print(f"OK: token saved to {TOKEN_FILE}")
    return True


def verify():
    """Verify existing token works."""
    if not os.path.exists(TOKEN_FILE):
        print("NO_TOKEN")
        return False

    with open(TOKEN_FILE) as f:
        token_data = json.load(f)

    import urllib.request

    req = urllib.request.Request(
        "https://www.googleapis.com/oauth2/v1/tokeninfo",
        headers={"Authorization": f"Bearer {token_data['token']}"},
    )

    try:
        with urllib.request.urlopen(req) as resp:
            info = json.loads(resp.read().decode())
            print(f"OK: token valid for scope(s): {info.get('scope', 'unknown')}")
            return True
    except urllib.error.HTTPError:
        # Try refreshing
        client_id = token_data.get("client_id")
        client_secret = token_data.get("client_secret")
        refresh_token = token_data.get("refresh_token")

        if not refresh_token:
            print("INVALID: no refresh_token")
            return False

        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        encoded = "&".join(f"{k}={v}" for k, v in data.items()).encode()
        req2 = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=encoded,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        try:
            with urllib.request.urlopen(req2) as resp2:
                tokens = json.loads(resp2.read().decode())
                token_data["token"] = tokens.get("access_token")
                with open(TOKEN_FILE, "w") as f:
                    json.dump(token_data, f, indent=2)
                print("OK: token refreshed and saved")
                return True
        except urllib.error.HTTPError as e:
            print(f"INVALID: refresh failed - {e}")
            return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <url|exchange|verify> [code]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "url":
        generate_url()
    elif cmd == "exchange":
        if len(sys.argv) < 3:
            print("Usage: gdrive_auth_helper.py exchange <AUTH_CODE>")
            sys.exit(1)
        exchange_code(sys.argv[2])
    elif cmd == "verify":
        ok = verify()
        sys.exit(0 if ok else 1)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
