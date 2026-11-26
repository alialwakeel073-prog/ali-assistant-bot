"""
Telegram smart-assistant bot for Ali.

- Primary AI: Groq (free tier), model openai/gpt-oss-120b,
  via the OpenAI-compatible endpoint https://api.groq.com/openai/v1
- Fallback AI: Google Gemini (Flash), via its OpenAI-compatible
  endpoint https://generativelanguage.googleapis.com/v1beta/openai/
  Used only if Groq fails, or if no Groq key is set.
- Hosting: Render free web service, webhook mode (production), or
  PythonAnywhere free (Flask WSGI webhook, see flask_app.py).
  Local testing: RUN_MODE=polling

All secrets come from environment variables. Nothing is hardcoded.
No real API call is made at import time, so the module can be
imported (and smoke-tested) without any keys set.
"""

import logging
import os

from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Load a local .env file if present (Render uses its own env vars).
load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (all from environment, never hardcoded)
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
RUN_MODE = os.getenv("RUN_MODE", "webhook").strip().lower()  # webhook | polling
PORT = int(os.getenv("PORT", "10000"))
# Render sets RENDER_EXTERNAL_URL automatically; WEBHOOK_URL is the manual
# alternative (e.g. https://your-app.onrender.com).
BASE_WEBHOOK_URL = (
    os.getenv("RENDER_EXTERNAL_URL", "") or os.getenv("WEBHOOK_URL", "")
).rstrip("/")

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "openai/gpt-oss-120b"

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODEL = "gemini-3.8-flash"
# If Gemini rejects the model above (model names change over time),
# this is the fallback string to try.
GEMINI_MODEL_FALLBACK = "gemini-2.5-flash"

# Optional allow-list: comma-separated Telegram user IDs, e.g. "123456,789012".
# If empty / unset, anyone who finds the bot can use it.
ALLOWED_USER_IDS = {
    int(x.strip())
    for x in os.getenv("ALLOWED_USER_IDS", "").split(",")
    if x.strip().isdigit()
}

# Keep only the last N exchanges (user + assistant) per user, so we stay
# well inside Groq's free-tier token limits.
MAX_EXCHANGES = 10

SYSTEM_PROMPT = (
    "You are a helpful personal assistant for Ali, a Senior Accountant "
    "based in Riyadh, Saudi Arabia. "
    "Answer in the same language the user writes in: if the user writes "
    "in Arabic, answer in Arabic (Egyptian dialect, simple and natural); "
    "if the user writes in English, answer in English. "
    "Be concise, practical and direct. Give clear steps when the user "
    "asks how to do something. Do not invent facts, prices, links or "
    "contact details. If you do not know something, say so plainly."
)

# In-memory conversation history: {telegram_user_id: [messages]}
# Each message is {"role": "user"|"assistant", "content": "..."}.
# History is intentionally in-memory only: restarting the bot clears it.
histories: dict[int, list[dict]] = {}


# ---------------------------------------------------------------------------
# AI helpers
# ---------------------------------------------------------------------------
# Proxy for outgoing traffic, if one is configured in the environment.
# PythonAnywhere free accounts must route all external traffic through
# their proxy (HTTP_PROXY / HTTPS_PROXY, e.g. http://proxy.server:3128).
# When no proxy is set this returns "" and everything behaves as before.
def _proxy_url() -> str:
    for key in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"):
        value = os.getenv(key, "").strip()
        if value:
            return value
    return ""


def _call_openai_compatible(api_key: str, base_url: str, model: str,
                            messages: list[dict]) -> str:
    """One chat-completion call against an OpenAI-compatible endpoint."""
    proxy = _proxy_url()
    if proxy:
        import httpx

        http_client = httpx.Client(proxy=proxy, timeout=60.0)
        client = OpenAI(api_key=api_key, base_url=base_url,
                        http_client=http_client)
    else:
        client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
        max_tokens=1000,
    )
    return (response.choices[0].message.content or "").strip()


def _trim_history(user_id: int) -> None:
    """Keep only the last MAX_EXCHANGES exchanges (2 messages each)."""
    history = histories.get(user_id, [])
    histories[user_id] = history[-(MAX_EXCHANGES * 2):]


def get_ai_reply(user_id: int, user_text: str) -> str:
    """
    Get a reply for one user message, trying Groq first and Gemini
    as a fallback. Never raises: on total failure it returns a
    polite Arabic error message instead.
    """
    history = histories.setdefault(user_id, [])
    history.append({"role": "user", "content": user_text})
    _trim_history(user_id)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + histories[user_id]

    errors: list[str] = []

    # 1) Primary: Groq
    if GROQ_API_KEY:
        try:
            reply = _call_openai_compatible(
                GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL, messages)
            if reply:
                history.append({"role": "assistant", "content": reply})
                _trim_history(user_id)
                return reply
        except Exception as exc:  # noqa: BLE001 - fall through to Gemini
            errors.append(f"Groq: {exc}")
            logger.warning("Groq call failed, trying Gemini: %s", exc)
    else:
        errors.append("Groq: no GROQ_API_KEY set")

    # 2) Fallback: Gemini (Flash)
    if GEMINI_API_KEY:
        for model in (GEMINI_MODEL, GEMINI_MODEL_FALLBACK):
            try:
                reply = _call_openai_compatible(
                    GEMINI_API_KEY, GEMINI_BASE_URL, model, messages)
                if reply:
                    history.append({"role": "assistant", "content": reply})
                    _trim_history(user_id)
                    return reply
            except Exception as exc:  # noqa: BLE001 - try next model / give up
                errors.append(f"Gemini ({model}): {exc}")
                logger.warning("Gemini call failed for %s: %s", model, exc)

    logger.error("All AI providers failed: %s", "; ".join(errors))
    return (
        "معلش، حصلت مشكلة دلوقتي ومقدرتش أرد. "
        "جرّب تاني بعد شوية، ولو المشكلة فضلت، اتأكد إن مفتاح Groq "
        "شغال ولسه مخلصش الحد اليومي المجاني."
    )


def is_allowed(user_id: int) -> bool:
    """True if the user may use the bot (allow-list off = everyone)."""
    return not ALLOWED_USER_IDS or user_id in ALLOWED_USER_IDS


# ---------------------------------------------------------------------------
# Telegram handlers (user-facing strings in Arabic)
# ---------------------------------------------------------------------------
START_TEXT = (
    "أهلاً يا علي! 👋\n\n"
    "أنا مساعدك الذكي على تليجرام. ابعتلي أي سؤال أو أي حاجة "
    "عايز مساعدة فيها، وأنا هرد عليك على طول.\n\n"
    "أوامر مفيدة:\n"
    "/help - شرح الأوامر\n"
    "/new - بداية محادثة جديدة (بيمسح ذاكرة المحادثة)\n"
    "/clear - نفس /new\n\n"
    "ملحوظة: أنا برد على الرسايل النصية بس دلوقتي."
)

HELP_TEXT = (
    "دي الأوامر اللي أقدر أعملها:\n\n"
    "/start - بداية وتعارف\n"
    "/help - عرض المساعدة دي\n"
    "/new - محادثة جديدة (مسح ذاكرة المحادثة)\n"
    "/clear - نفس /new\n\n"
    "غير كده، ابعتلي سؤالك كتابة وأنا هرد عليك. "
    "بفتكر آخر 10 رسايل في المحادثة عشان أرد في السياق."
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text(
            "معلش، البوت ده خاص بصاحبه بس.")
        return
    await update.message.reply_text(START_TEXT)


async def help_command(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text(
            "معلش، البوت ده خاص بصاحبه بس.")
        return
    await update.message.reply_text(HELP_TEXT)


async def clear_history(update: Update,
                        context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forget the conversation history for this user (/new and /clear)."""
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text(
            "معلش، البوت ده خاص بصاحبه بس.")
        return
    histories.pop(update.effective_user.id, None)
    await update.message.reply_text(
        "تمام، بدأنا محادثة جديدة. ابعتلي سؤالك. 🙂")


async def handle_text(update: Update,
                      context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_allowed(user.id):
        await update.message.reply_text(
            "معلش، البوت ده خاص بصاحبه بس.")
        return
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing")
    reply = get_ai_reply(user.id, update.message.text)
    await update.message.reply_text(reply)


async def handle_non_text(update: Update,
                          context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text(
            "معلش، البوت ده خاص بصاحبه بس.")
        return
    await update.message.reply_text(
        "معلش، أنا برد على الرسايل النصية بس دلوقتي. "
        "ابعتلي سؤالك كتابة.")


def build_application() -> Application:
    """Build the Telegram application. Requires TELEGRAM_BOT_TOKEN."""
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. "
            "Set it in your .env file or in the hosting environment variables.")
    builder = Application.builder().token(TELEGRAM_BOT_TOKEN)
    # PythonAnywhere free: route Telegram traffic through the proxy.
    proxy = _proxy_url()
    if proxy:
        builder = builder.proxy(proxy)
    app = builder.build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("new", clear_history))
    app.add_handler(CommandHandler("clear", clear_history))
    # Text messages first, then anything else (photo, voice, sticker...).
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,
                                   handle_text))
    app.add_handler(MessageHandler(~filters.TEXT & ~filters.COMMAND,
                                   handle_non_text))
    return app


def get_webhook_url() -> str:
    """Full webhook URL Telegram will call, e.g. https://app.onrender.com/<token>."""
    if not BASE_WEBHOOK_URL:
        raise RuntimeError(
            "Set RENDER_EXTERNAL_URL (set automatically by Render) "
            "or WEBHOOK_URL to your public app URL.")
    return f"{BASE_WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}"


def main() -> None:
    app = build_application()
    if RUN_MODE == "polling":
        logger.info("Starting in polling mode (local testing only).")
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        return

    # Production: webhook mode on Render.
    webhook_url = get_webhook_url()
    logger.info("Starting in webhook mode on port %s.", PORT)
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TELEGRAM_BOT_TOKEN,
        webhook_url=webhook_url,
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()
