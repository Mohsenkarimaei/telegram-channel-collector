import os
import re
import logging
from decimal import Decimal, ROUND_HALF_UP

import aiohttp
from dotenv import load_dotenv
from telethon import TelegramClient, events

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mk-collector")

API_ID = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
SOURCE = os.getenv("TELEGRAM_SOURCE", "@BarbieLand_shop")
DESTINATION = os.getenv("TELEGRAM_DESTINATION", "@manto_omde_mk")
SOURCE_CODE = os.getenv("SOURCE_CODE", "CH-001")
PRICE_TYPE = os.getenv("PRICE_TYPE", "percent")
PRICE_VALUE = Decimal(os.getenv("PRICE_VALUE", "0"))
WHATSAPP = os.getenv("WHATSAPP_NUMBER", "09384712198")
ORDER_ID = os.getenv("ORDER_ID", "@pakhshe_mk")
SESSION = os.getenv("SESSION_NAME", "mk_collector")

PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

REMOVE_LINE_PATTERNS = [
    r"(?:https?://|www\.)\S+",
    r"(?:واتساپ|whatsapp|تلگرام|telegram)\s*[:：]?\s*\+?\d[\d\s\-()]{7,}",
    r"(?:جهت سفارش|برای سفارش|سفارش|تماس|ارتباط|خرید)\s*[:：]?.*",
    r"(?:@)[A-Za-z0-9_]{3,}",
    r"پوشاک\s*باربی\s*لند",
]

PRICE_RE = re.compile(r"(قیمت\s*[:：]?\s*)([۰-۹٠-٩\d][۰-۹٠-٩\d,،.]*)", re.I)
PHONE_RE = re.compile(r"(?:\+?98|0098|0)?9\d{9}|(?:\+?98|0098)\s*9(?:[\s-]?\d){9}")


def normalize_digits(text: str) -> str:
    return text.translate(PERSIAN_DIGITS).replace("،", ",")


def parse_number(raw: str) -> Decimal:
    return Decimal(re.sub(r"[^0-9.]", "", normalize_digits(raw)))


def format_number(value: Decimal) -> str:
    if value == value.to_integral():
        return f"{int(value):,}".replace(",", "،")
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):,}".replace(",", "،")


def adjust_price(value: Decimal) -> Decimal:
    if PRICE_TYPE == "fixed":
        return value + PRICE_VALUE
    return value * (Decimal("1") + PRICE_VALUE / Decimal("100"))


def clean_caption(caption: str) -> str:
    lines = []
    for raw_line in caption.splitlines():
        line = raw_line.strip()
        if not line:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        # Remove source phone numbers before other checks.
        line = PHONE_RE.sub("", line).strip()
        if not line:
            continue
        if any(re.search(pattern, line, re.I) for pattern in REMOVE_LINE_PATTERNS):
            continue
        # Remove remaining @handles, but keep no source handle in product text.
        line = re.sub(r"@[A-Za-z0-9_]{3,}", "", line).strip()
        line = re.sub(r"\s{2,}", " ", line)
        if line:
            lines.append(line)

    cleaned = "\n".join(lines).strip()
    # Apply the configured price change to every explicit 'قیمت:' field.
    def repl(match):
        old = parse_number(match.group(2))
        return match.group(1) + format_number(adjust_price(old))

    cleaned = PRICE_RE.sub(repl, cleaned)
    footer = f"جهت سفارش👇\n\nواتساپ : {WHATSAPP}\n🆔 {ORDER_ID}"
    return f"{cleaned}\n\n{footer}" if cleaned else footer


async def send_via_bot_api(text: str, media=None):
    base = f"https://api.telegram.org/bot{BOT_TOKEN}"
    async with aiohttp.ClientSession() as session:
        if media is None:
            async with session.post(f"{base}/sendMessage", json={"chat_id": DESTINATION, "text": text}) as r:
                if r.status >= 300:
                    raise RuntimeError(f"sendMessage failed: {r.status} {await r.text()}")
            return
        # Media is downloaded by Telethon and uploaded to Bot API.
        method = "sendPhoto" if getattr(media, "__class__", None).__name__.lower().find("photo") >= 0 else "sendDocument"
        endpoint = f"{base}/{method}"
        data = aiohttp.FormData()
        data.add_field("chat_id", DESTINATION)
        data.add_field("caption", text)
        data.add_field("parse_mode", "HTML")
        data.add_field("photo" if method == "sendPhoto" else "document", media, filename="media")
        async with session.post(endpoint, data=data) as r:
            if r.status >= 300:
                raise RuntimeError(f"{method} failed: {r.status} {await r.text()}")


client = TelegramClient(SESSION, API_ID, API_HASH)


@client.on(events.NewMessage(chats=SOURCE))
async def on_new_post(event):
    try:
        caption = clean_caption(event.raw_text or "")
        log.info("Processing %s from %s", event.id, SOURCE)
        if event.media:
            media_bytes = await client.download_media(event.media, file=bytes)
            await send_via_bot_api(caption, media=media_bytes)
        else:
            await send_via_bot_api(caption)
        log.info("Published %s as %s", event.id, SOURCE_CODE)
    except Exception:
        log.exception("Failed to process source post %s", event.id)


async def main():
    await client.start()
    me = await client.get_me()
    log.info("Collector logged in as %s", getattr(me, "username", None) or me.id)
    log.info("Listening: %s (%s) -> %s", SOURCE, SOURCE_CODE, DESTINATION)
    await client.run_until_disconnected()


if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
