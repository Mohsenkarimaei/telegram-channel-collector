import os
from telethon.sync import TelegramClient

api_id = int(os.environ["TELEGRAM_API_ID"])
api_hash = os.environ["TELEGRAM_API_HASH"]

client = TelegramClient("mk_collector", api_id, api_hash)
client.start()
print("SESSION CREATED: mk_collector.session")
print("Keep this file private. Never upload it to GitHub.")
