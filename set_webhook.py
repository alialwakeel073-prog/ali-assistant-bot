#!/usr/bin/env python3
"""
Set (or delete) the Telegram webhook for Ali's bot.

Usage (from a PythonAnywhere Bash console, in the project directory):

    python3 set_webhook.py

    # Or pass the base URL directly:
    python3 set_webhook.py --url https://<username>.pythonanywhere.com

    # Delete the webhook (back to no webhook / polling):
    python3 set_webhook.py --delete

The webhook URL Telegram is told is plain <WEBHOOK_URL>/webhook
(no secret in the URL at all). Telegram sends the secret back in
the X-Telegram-Bot-Api-Secret-Token header with every update, and
the Flask app checks that header — server access logs record full
request URLs, so a secret in the path would leak there.

WEBHOOK_SECRET is a random secret you choose (32+ random characters)
— it is NOT the bot token. The token must never appear in a URL.

Secrets are read from the environment first; if they are not set,
this script reads them from the os.environ lines in the REAL
PythonAnywhere WSGI file at /var/www/*_pythonanywhere_com_wsgi.py
(the file you filled in on the Web tab — NOT wsgi.py in the repo).
The repo wsgi.py is committed to GitHub: NEVER put real secrets in
it. If no /var/www file exists (e.g. running locally), the repo
wsgi.py is read ONLY as a last resort, comment lines are skipped,
placeholder values are rejected, and a loud warning is printed.
NEVER type a token or secret in the Bash console: anything typed
there is saved in ~/.bash_history. If you ever did, run
`history -c && rm -f ~/.bash_history` afterwards.

No secrets are hardcoded: the token, secret and URL come from the
environment or wsgi.py (or the --url flag). Uses only the standard
library, and respects HTTP_PROXY / HTTPS_PROXY if set (needed on
PythonAnywhere free accounts, whose outgoing traffic goes through
a proxy).

Exit code 0 = Telegram accepted the request, 1 = it did not.
"""

import argparse
import glob
import json
import os
import sys
import urllib.error
import urllib.request

TELEGRAM_API = "https://api.telegram.org"

# Substrings that mark a value as a placeholder/example, never a real
# secret. A real token/key/secret is plain ASCII with no spaces or
# angle brackets; anything matching these is rejected, never used.
_PLACEHOLDER_MARKERS = (
    "paste-", "paste_", "<", ">", "...", "example", "username",
    "حط هنا", "التوكن", "مفتاح", "سر عشوائي",
)


def _is_placeholder(value: str) -> bool:
    """True when a value is an example/placeholder, not a real secret."""
    if not value or not value.strip():
        return True
    lowered = value.strip().lower()
    if any(marker in lowered for marker in _PLACEHOLDER_MARKERS):
        return True
    # Real secrets are ASCII; a value with non-ASCII text is a
    # human-language placeholder (e.g. Arabic example text).
    try:
        value.strip().encode("ascii")
    except UnicodeEncodeError:
        return True
    return False


def _parse_wsgi_env(path: str) -> dict:
    """Read os.environ[...] = "..." lines from one WSGI file.

    Comment lines (starting with # after stripping) are SKIPPED —
    a commented example must never be taken as a real value.
    Placeholder values are rejected by _is_placeholder().
    """
    import re

    values: dict = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                match = re.search(
                    r'os\.environ\["([A-Z_]+)"\]\s*=\s*"([^"]*)"', line)
                if match and not _is_placeholder(match.group(2)):
                    values[match.group(1)] = match.group(2)
    except Exception:  # noqa: BLE001 - env vars are the primary source
        pass
    return values


def _read_wsgi_env() -> tuple[dict, str]:
    """Find the real secrets, in order:

    1. /var/www/*_pythonanywhere_com_wsgi.py — the REAL WSGI file on
       PythonAnywhere (first glob match, sorted). This is where the
       real values live.
    2. wsgi.py next to this script (the repo copy) — LAST RESORT
       only, and only for non-comment, non-placeholder lines. Real
       secrets must NEVER be in the repo copy (it is committed to
       GitHub); if a value comes from here, a warning is printed.

    Returns (values, source_description).
    """
    var_www = sorted(glob.glob("/var/www/*_pythonanywhere_com_wsgi.py"))
    for path in var_www:
        values = _parse_wsgi_env(path)
        if values:
            return values, f"PythonAnywhere WSGI file {path}"
    repo_wsgi = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "wsgi.py")
    values = _parse_wsgi_env(repo_wsgi)
    if values:
        print(
            "WARNING: secrets were read from the REPO wsgi.py "
            f"({repo_wsgi}). Real secrets must live ONLY in the "
            "/var/www WSGI file on PythonAnywhere — the repo copy "
            "is committed to GitHub. Move them there.",
            file=sys.stderr)
        return values, f"repo wsgi.py {repo_wsgi} (WARNING: not for real secrets)"
    return {}, "none"


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

    wsgi_env, wsgi_source = _read_wsgi_env()
    token = (os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
             or wsgi_env.get("TELEGRAM_BOT_TOKEN", "").strip())
    if _is_placeholder(token):
        print("ERROR: TELEGRAM_BOT_TOKEN is not set to a real value "
              f"(env or {wsgi_source}). Set it in the /var/www WSGI "
              "file on PythonAnywhere — never in the repo wsgi.py.",
              file=sys.stderr)
        return 1
    secret = (os.getenv("WEBHOOK_SECRET", "").strip()
              or wsgi_env.get("WEBHOOK_SECRET", "").strip())
    if _is_placeholder(secret):
        print("ERROR: WEBHOOK_SECRET is not set to a real value "
              f"(env or {wsgi_source}). Set a random secret (not the "
              "bot token) in the /var/www WSGI file on PythonAnywhere.",
              file=sys.stderr)
        return 1

    if args.delete:
        result = _telegram_post(token, "deleteWebhook",
                                {"drop_pending_updates": True})
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 1

    base_url = (args.url or os.getenv("WEBHOOK_URL", "")
                or wsgi_env.get("WEBHOOK_URL", "")).strip().rstrip("/")
    if _is_placeholder(base_url):
        print("ERROR: set WEBHOOK_URL to a real value or pass --url "
              "(e.g. https://<username>.pythonanywhere.com — with "
              "your real username).",
              file=sys.stderr)
        return 1

    # Plain URL, no secret in it. The secret goes in the
    # secret_token field: Telegram sends it back in the
    # X-Telegram-Bot-Api-Secret-Token header with every update.
    webhook_url = f"{base_url}/webhook"
    result = _telegram_post(token, "setWebhook", {
        "url": webhook_url,
        "secret_token": secret,
        "allowed_updates": ["message", "callback_query"],
    })
    # The URL contains no secret, so it is safe to print.
    print(f"Webhook URL: {webhook_url} (secret sent via header, hidden)")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("ok"):
        print("OK — webhook set. Send /start to the bot on Telegram.")
        return 0
    print("ERROR: Telegram did not accept the webhook.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
