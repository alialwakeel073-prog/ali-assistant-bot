# WSGI entry point for PythonAnywhere.
#
# On PythonAnywhere, open the "WSGI configuration file" link in the
# Web tab and replace its contents with the contents of THIS file
# (e.g. /home/<username>/ali-assistant-bot/wsgi.py), then fill in
# your values below. PythonAnywhere loads the variable called
# `application` from that WSGI file.
#
# Set the secrets as environment variables BEFORE importing the app.
# Replace <username> with your PythonAnywhere username and paste your
# real values (never commit a wsgi.py with real keys to GitHub — keep
# the placeholders here and fill them in on PythonAnywhere only):
#
#   os.environ["TELEGRAM_BOT_TOKEN"] = "123456:ABC-DEF..."
#   os.environ["GROQ_API_KEY"] = "gsk_..."
#   os.environ["GEMINI_API_KEY"] = "AIza..."   # optional fallback
#   os.environ["RUN_MODE"] = "webhook"
#   os.environ["WEBHOOK_URL"] = "https://<username>.pythonanywhere.com"
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
# os.environ.setdefault("WEBHOOK_URL", "https://<username>.pythonanywhere.com")

from flask_app import app as application  # noqa: E402
