"""
Flask WSGI wrapper for Ali's Telegram bot — PythonAnywhere version.

PythonAnywhere free hosting runs a WSGI app (no long-running process,
no Render-style webhook server), so this file exposes the bot as a
plain Flask app:

- GET  /                     -> health check, "OK" (no keys needed)
- POST /<TELEGRAM_BOT_TOKEN> -> Telegram webhook endpoint. The token
  in the URL path is the secret, exactly like Render's url_path.

The python-telegram-bot Application is created once and lives on a
dedicated asyncio event loop running in a background thread, because
Flask/WSGI is synchronous and PTB is async. The app is only built
lazily on the first webhook request, so importing this module (and
the health check) works with no keys set.

Proxy: on PythonAnywhere free accounts all outgoing traffic must go
through the proxy at http://proxy.server:3128, set via the
HTTP_PROXY / HTTPS_PROXY env vars. bot.py reads those vars and passes
them to both the Telegram client and the OpenAI clients, so nothing
else is needed here.

No secrets are hardcoded. All config comes from environment variables
(on PythonAnywhere, set them in the WSGI file — see wsgi.py).
"""

import asyncio
import logging
import os
import threading

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, request
from telegram import Update

load_dotenv()

logger = logging.getLogger(__name__)

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Lazy PTB application on a dedicated event loop (background thread)
# ---------------------------------------------------------------------------
_ptb_app = None
_loop = None
_loop_thread = None
# RLock, not Lock: _ensure_ptb_app() holds this while calling _run(),
# which in turn calls _ensure_loop(), which also takes this lock.
_lock = threading.RLock()


def _ensure_loop() -> asyncio.AbstractEventLoop:
    """Start (once) a background thread running an asyncio event loop."""
    global _loop, _loop_thread
    if _loop is not None:
        return _loop
    with _lock:
        if _loop is not None:
            return _loop
        loop = asyncio.new_event_loop()

        def _run() -> None:
            asyncio.set_event_loop(loop)
            loop.run_forever()

        thread = threading.Thread(target=_run, daemon=True,
                                  name="ptb-event-loop")
        thread.start()
        _loop, _loop_thread = loop, thread
        return loop


def _run(coro):
    """Run a coroutine on the background loop and wait for its result."""
    loop = _ensure_loop()
    return asyncio.run_coroutine_threadsafe(coro, loop).result(timeout=60)


def _ensure_ptb_app():
    """Build + initialise the PTB Application once (lazy, needs the token)."""
    global _ptb_app
    if _ptb_app is not None:
        return _ptb_app
    with _lock:
        if _ptb_app is not None:
            return _ptb_app
        # Imported here, not at module top, so importing flask_app never
        # fails when TELEGRAM_BOT_TOKEN is not set yet.
        from bot import build_application

        ptb_app = build_application()
        _run(ptb_app.initialize())
        _run(ptb_app.start())
        _ptb_app = ptb_app
        logger.info("Telegram application initialised (PythonAnywhere/Flask).")
        return ptb_app


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def health_check():
    """Health check — works with no keys set, used by PythonAnywhere."""
    return jsonify({"status": "ok", "bot": "ali-assistant-bot"}), 200


@app.route("/<path:token>", methods=["POST"])
def telegram_webhook(token: str):
    """Telegram webhook endpoint. The token in the path is the secret."""
    expected = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not expected or token != expected:
        abort(403)

    data = request.get_json(force=True, silent=True)
    if not isinstance(data, dict):
        abort(400)

    try:
        ptb_app = _ensure_ptb_app()
        update = Update.de_json(data, ptb_app.bot)
        # Always answer 200 to Telegram, even if one handler fails —
        # otherwise Telegram retries the same update forever.
        try:
            _run(ptb_app.process_update(update))
        except Exception:  # noqa: BLE001 - log, still return 200
            logger.exception("Error processing Telegram update")
    except Exception:  # noqa: BLE001 - e.g. missing/invalid token
        logger.exception("Could not initialise Telegram application")
        return jsonify({"status": "error",
                        "error": "telegram application unavailable"}), 500
    return jsonify({"status": "ok"}), 200


@app.route("/<path:token>", methods=["GET"])
def webhook_get(token: str):
    """Telegram never GETs the webhook; answer plainly instead of 404."""
    abort(405)
