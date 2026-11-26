#!/usr/bin/env python3
"""
Set (or delete) the Telegram webhook for Ali's bot.

Usage (from a PythonAnywhere Bash console, in the project directory):

    # Set the webhook to your PythonAnywhere web app URL:
    export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
    export WEBHOOK_URL="https://<username>.pythonanywhere.com"
    python3 set_webhook.py

    # Or pass the URL directly:
    python3 set_webhook.py --url https://<username>.pythonanywhere.com

    # Delete the webhook (back to no webhook / polling):
    python3 set_webhook.py --delete

The full webhook URL sent to Telegram is
    <WEBHOOK_URL>/<TELEGRAM_BOT_TOKEN>

No secrets are hardcoded: the token and URL come from the
environment (or the --url flag). Uses only the standard library, and
respects HTTP_PROXY / HTTPS_PROXY if set (needed on PythonAnywhere
free accounts, whose outgoing traffic goes through a proxy).

Exit code 0 = Telegram accepted the request, 1 = it did not.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

TELEGRAM_API = "https://api.telegram.org"


def _telegram_post(token: str, method: str, payload: dict) -> dict:
    """POST one JSON call to the Telegram Bot API (proxy-aware)."""
    url = f"{TELEGRAM_API}/bot{token}/{method}"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    # ProxyHandler() with no arguments reads HTTP_PROXY/HTTPS_PROXY
    # from the environment — required on PythonAnywhere free.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler())
    try:
        with opener.open(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            return {"ok": False, "description": f"HTTP {exc.code}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "description": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Set/delete Telegram webhook")
    parser.add_argument("--url", default="",
                        help="Base web app URL, e.g. "
                             "https://<username>.pythonanywhere.com")
    parser.add_argument("--delete", action="store_true",
                        help="Delete the webhook instead of setting it")
    args = parser.parse_args()

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN is not set.", file=sys.stderr)
        return 1

    if args.delete:
        result = _telegram_post(token, "deleteWebhook",
                                {"drop_pending_updates": True})
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 1

    base_url = (args.url or os.getenv("WEBHOOK_URL", "")).strip().rstrip("/")
    if not base_url:
        print("ERROR: set WEBHOOK_URL or pass --url "
              "(e.g. https://<username>.pythonanywhere.com)",
              file=sys.stderr)
        return 1

    webhook_url = f"{base_url}/{token}"
    result = _telegram_post(token, "setWebhook", {
        "url": webhook_url,
        "allowed_updates": ["message", "callback_query"],
    })
    print(f"Webhook URL: {webhook_url}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("ok"):
        print("OK — webhook set. Send /start to the bot on Telegram.")
        return 0
    print("ERROR: Telegram did not accept the webhook.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
