import logging
import os
import re
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.errors import RPCError
from telethon.sessions import StringSession

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mk-collector")


def required(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


try:
    API_ID = int(required("TELEGRAM_API_ID"))
except ValueError as exc:
    raise RuntimeError("TELEGRAM_API_ID must be a number") from exc

API_HASH = required("TELEGRAM_API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
SESSION_STRING = os.getenv("TELEGRAM_SESSION_STRING", "").strip()
SOURCE = os.getenv("TELEGRAM_SOURCE", "@BarbieLand_shop").strip()
DESTINATION = os.getenv("TELEGRAM_DESTINATION", "@manto_omde_mk").strip()
SOURCE_CODE = os.getenv("SOURCE_CODE", "CH-001").strip()
PRICE_TYPE = os.getenv("PRICE_TYPE", "percent").strip().lower()
WHATSAPP = os.getenv("WHATSAPP_NUMBER", os.getenv("WHATSAPP", "")).strip()
ORDER_ID = os.getenv("ORDER_ID", "@pakhshe_mk").strip()

try:
    PRICE_VALUE = Decimal(os.getenv("PRICE_VALUE", "0").strip())
except InvalidOperation as exc:
    raise RuntimeError("PRICE_VALUE must be a number") from exc

if not SOURCE or not DESTINATION:
    raise RuntimeError("TELEGRAM_SOURCE and TELEGRAM_DESTINATION cannot be empty")
if PRICE_TYPE not in {"percent", "fixed"}:
    raise RuntimeError("PRICE_TYPE must be 'percent' or 'fixed'")
if not BOT_TOKEN and not SESSION_STRING:
    raise RuntimeError("Set BOT_TOKEN or TELEGRAM_SESSION_STRING")

PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
PRICE_RE = re.compile(r"(قیمت\s*[:：]?\s*)([۰-۹٠-٩\d][۰-۹٠-٩\d,،.]*)", re.I)
PHONE_RE = re.compile(r"(?:\+?98|0098)?\s*9(?:[\s-]?\d){9}|0?9\d{9}")
HANDLE_RE = re.compile(r"@[A-Za-z0-9_]{3,}")
URL_RE = re.compile(r"(?:https?://|www\.)\S+|t\.me/\S+", re.I)


def normalize_digits(text):
    return text.translate(PERSIAN_DIGITS).replace("،", ",")


def parse_number(raw):
    cleaned = re.sub(r"[^0-9.]", "", normalize_digits(raw))
    return Decimal(cleaned) if cleaned else Decimal("0")


def format_number(value):
    value = value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"{int(value):,}".replace(",", "،")


def adjust_price(value):
    if PRICE_TYPE == "fixed":
        return value + PRICE_VALUE
    return value * (Decimal("1") + PRICE_VALUE / Decimal("100"))


def clean_caption(caption):
    kept = []
    for raw in caption.splitlines():
        line = raw.strip()
        if not line:
            if kept and kept[-1] != "":
                kept.append("")
            continue

        line = PHONE_RE.sub("", line)
        line = URL_RE.sub("", line)
        line = HANDLE_RE.sub("", line)
        line = re.sub(r"پوشاک\s*باربی\s*لند", "", line, flags=re.I).strip()

        if re.match(r"^(جهت سفارش|برای سفارش|تماس|ارتباط|خرید)\b", line, re.I):
            continue
        if re.match(r"^(واتساپ|whatsapp|تلگرام|telegram)\b", line, re.I):
            continue

        line = re.sub(r"\s{2,}", " ", line).strip()
        if line:
            kept.append(line)

    text = "\n".join(kept).strip()

    def price_repl(match):
        old = parse_number(match.group(2))
        return match.group(1) + format_number(adjust_price(old))

    text = PRICE_RE.sub(price_repl, text)
    footer = f"جهت سفارش👇\n\nواتساپ : {WHATSAPP}\n🆔 {ORDER_ID}"
    return f"{text}\n\n{footer}" if text else footer


# A saved user session is preferred when the source channel is not accessible
# to the bot account. Otherwise use BOT_TOKEN so Railway never asks for a phone/code.
if SESSION_STRING:
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    RUN_MODE = "user-session"
else:
    client = TelegramClient("bot_session", API_ID, API_HASH)
    RUN_MODE = "bot"


@client.on(events.NewMessage(chats=SOURCE))
async def on_new_post(event):
    try:
        caption = clean_caption(event.raw_text or "")
        if event.media:
            await client.send_file(DESTINATION, event.media, caption=caption)
        else:
            await client.send_message(DESTINATION, caption)
        log.info("Published source=%s code=%s message=%s", SOURCE, SOURCE_CODE, event.id)
    except Exception:
        log.exception("Failed to process source message %s", event.id)


async def main():
    try:
        if RUN_MODE == "user-session":
            await client.start()
        else:
            await client.start(bot_token=BOT_TOKEN)

        me = await client.get_me()
        identity = getattr(me, "username", None) or getattr(me, "id", "unknown")
        log.info("Telegram connected: account=%s mode=%s", identity, RUN_MODE)
        log.info("Collector: %s (%s) -> %s", SOURCE, SOURCE_CODE, DESTINATION)
        if RUN_MODE == "bot":
            log.warning("Bot mode: source channel must be accessible to this bot")
        if not WHATSAPP:
            log.warning("WHATSAPP_NUMBER/WHATSAPP is empty; footer will contain a blank number")
        await client.run_until_disconnected()
    except RPCError:
        log.exception("Telegram API error. Check channel access and Telegram credentials.")
        raise
    except Exception:
        log.exception("Collector stopped unexpectedly")
        raise


if __name__ == "__main__":
    client.loop.run_until_complete(main())
