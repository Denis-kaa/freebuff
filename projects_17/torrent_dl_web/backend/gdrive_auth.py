#!/usr/bin/env python3
"""
Google Drive OAuth 2.0 Authorization Script (headless server).

Usage:
    cd backend
    source venv/bin/activate
    python gdrive_auth.py

Flow:
    1. Prints authorization URL
    2. User opens URL in browser, authorizes the app
    3. User pastes the authorization code back
    4. Script saves token.json
"""

import json
import os
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

CREDENTIALS_FILE = os.getenv("GOOGLE_DRIVE_CREDENTIALS_FILE", "credentials.json")
TOKEN_FILE = os.getenv("GOOGLE_DRIVE_TOKEN_FILE", "token.json")


def main():
    # Check credentials file
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ Файл {CREDENTIALS_FILE} не найден.")
        print("   Скачайте его из Google Cloud Console:")
        print("   https://console.cloud.google.com/apis/credentials")
        sys.exit(1)

    # Check if token already exists
    if os.path.exists(TOKEN_FILE):
        print(f"⚠️  Файл {TOKEN_FILE} уже существует.")
        resp = input("   Перезаписать? (y/N): ").strip().lower()
        if resp != "y":
            print("Отмена.")
            sys.exit(0)

    # Create OAuth flow with console-based redirect
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)

    # For headless: use offline access with console redirect
    # This generates a URL + code flow instead of localhost server
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",  # Force consent to get refresh_token
    )

    print("=" * 60)
    print("🔐 Google Drive Authorization")
    print("=" * 60)
    print()
    print("1. Откройте эту ссылку в браузере:")
    print()
    print(f"   {auth_url}")
    print()
    print("2. Выберите аккаунт и разрешите доступ.")
    print("3. Скопируйте код авторизации и вставьте сюда.")
    print()

    auth_code = input("📋 Вставьте код авторизации: ").strip()

    if not auth_code:
        print("❌ Код не введён. Отмена.")
        sys.exit(1)

    # Exchange code for tokens
    try:
        flow.fetch_token(code=auth_code)
    except Exception as e:
        print(f"❌ Ошибка обмена кода на токен: {e}")
        sys.exit(1)

    creds = flow.credentials

    # Save token
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes),
    }

    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    print()
    print("=" * 60)
    print("✅ Токен сохранён в", TOKEN_FILE)
    print()
    print("Теперь включите Google Drive в .env:")
    print("   GOOGLE_DRIVE_ENABLED=true")
    print()
    print("Запустите бэкенд:")
    print("   uvicorn src.main:app --host 0.0.0.0 --port 8001")
    print("=" * 60)


if __name__ == "__main__":
    main()
