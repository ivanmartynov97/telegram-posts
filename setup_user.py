#!/usr/bin/env python3
import asyncio, os
from telethon import TelegramClient

BASE     = os.path.dirname(os.path.abspath(__file__))
SESSION  = os.path.join(BASE, "tg_user_session")
API_ID   = 39578814
API_HASH = "18f9ab304c0119a6ab28ff913f02f192"

async def main():
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.start()  # спросит номер, потом код из Telegram
    me = await client.get_me()
    print(f"\n✅ Авторизован: {me.first_name} (@{me.username})")
    print("Сессия сохранена. Теперь fetch_views.py будет работать.")
    await client.disconnect()

asyncio.run(main())
