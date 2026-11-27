# WSGI entry point for PythonAnywhere.
#
# On PythonAnywhere, open the "WSGI configuration file" link in the
# Web tab and replace its contents with the contents of THIS file
# (e.g. /home/<username>/ali-assistant-bot/wsgi.py), then fill in
# your values below. PythonAnywhere loads the variable called
# `application` from that WSGI file.
#
# Set the secrets as environment variables BEFORE importing the app.
# Fill them in on PythonAnywhere ONLY — NEVER put real values in
# this repo file, because it is committed to GitHub. Real secrets
# live ONLY in the /var/www WSGI file on PythonAnywhere. The
# examples below are deliberately empty, so that set_webhook.py
# (which rejects placeholder values) can never mistake them for
# real values:
#
#   os.environ["TELEGRAM_BOT_TOKEN"] = ""
#   os.environ["GROQ_API_KEY"] = ""
#   os.environ["GEMINI_API_KEY"] = ""   # optional fallback
#   os.environ["RUN_MODE"] = "webhook"
#   os.environ["WEBHOOK_URL"] = ""
#   # WEBHOOK_SECRET: a random secret YOU choose (32+ random characters,
#   # e.g. from `python3 -c "import secrets; print(secrets.token_hex(32))"`).
#   # Telegram sends it back in the X-Telegram-Bot-Api-Secret-Token
#   # header with every update — it NEVER appears in any URL, because
#   # server access logs record full request URLs. Set the same value
#   # here and Telegram will be told it by set_webhook.py.
#   os.environ["WEBHOOK_SECRET"] = ""
#
# PythonAnywhere free accounts must use the proxy for outgoing
# traffic; the proxy is already configured in the account, and bot.py
# picks it up from HTTP_PROXY / HTTPS_PROXY if they are set. If your
# account sets them, do NOT override them here.

import os
import sys

# Make sure the project directory is on the import path, so
# `flask_app` and `bot` are found regardless of the working directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# --- Fill in your values on PythonAnywhere (see the comments above) ---
# os.environ.setdefault("TELEGRAM_BOT_TOKEN", "")
# os.environ.setdefault("GROQ_API_KEY", "")
# os.environ.setdefault("GEMINI_API_KEY", "")
# os.environ.setdefault("RUN_MODE", "webhook")
# os.environ.setdefault("WEBHOOK_URL", "")
# os.environ.setdefault("WEBHOOK_SECRET", "")
# Your Telegram user ID only (from @userinfobot), so only you can use
# the bot. CLOSED BY DEFAULT: if ALLOWED_USER_IDS is empty / unset,
# the bot answers NOBODY — you MUST set your numeric ID here.
# Never put a real ID in a file committed to GitHub — set it here, on
# PythonAnywhere only.
# os.environ.setdefault("ALLOWED_USER_IDS", "")

from flask_app import app as application  # noqa: E402
