import os
import re
import logging
from decimal import Decimal, ROUND_HALF_UP

from dotenv import load_dotenv
from telethon import TelegramClient, events

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mk-collector")

API_ID = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
SOURCE = os.getenv("TELEGRAM_SOURCE", "@BarbieLand_shop")
DESTINATION = os.getenv("TELEGRAM_DESTINATION", "@manto_omde_mk")
SOURCE_CODE = os.getenv("SOURCE_CODE", "CH-001")
PRICE_TYPE = os.getenv("PRICE_TYPE", "percent")
PRICE_VALUE = Decimal(os.getenv("PRICE_VALUE", "0"))
WHATSAPP = os.getenv("WHATSAPP_NUMBER", "09384712198")
ORDER_ID = os.getenv("ORDER_ID", "@pakhshe_mk")
SESSION = os.getenv("SESSION_NAME", "mk_collector")

PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
PRICE_RE = re.compile(r"(قیمت\s*[:：]?\s*)([۰-۹٠-٩\d][۰-۹٠-٩\d,،.]*)", re.I)
PHONE_RE = re.compile(r"(?:\+?98|0098)?\s*9(?:[\s-]?\d){9}|0?9\d{9}")
HANDLE_RE = re.compile(r"@[A-Za-z0-9_]{3,}")
URL_RE = re.compile(r"(?:https?://|www\.)\S+|t\.me/\S+", re.I)


def normalize_digits(text):
    return text.translate(PERSIAN_DIGITS).replace("،", ",")


def parse_number(raw):
    return Decimal(re.sub(r"[^0-9.]", "", normalize_digits(raw)))


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

        # Remove source contact information and links.
        line = PHONE_RE.sub("", line)
        line = URL_RE.sub("", line)
        line = HANDLE_RE.sub("", line)
        line = re.sub(r"پوشاک\s*باربی\s*لند", "", line, flags=re.I).strip()

        # Remove lines that are purely source ordering/contact/advertising text.
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


client = TelegramClient(SESSION, API_ID, API_HASH)


@client.on(events.NewMessage(chats=SOURCE))
async def on_new_post(event):
    try:
        caption = clean_caption(event.raw_text or "")
        if event.media:
            # Telethon preserves the original media while letting us replace the caption.
            await client.send_file(DESTINATION, event.media, caption=caption)
        else:
            await client.send_message(DESTINATION, caption)
        log.info("Published source=%s code=%s message=%s", SOURCE, SOURCE_CODE, event.id)
    except Exception:
        log.exception("Failed to process message %s", event.id)


async def main():
    # User session is used for reading source channels; BOT_TOKEN is used only as a required deployment secret.
    await client.start()
    me = await client.get_me()
    log.info("Logged in as %s", getattr(me, "username", None) or me.id)
    log.info("Listening: %s (%s) -> %s", SOURCE, SOURCE_CODE, DESTINATION)
    await client.run_until_disconnected()


if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
