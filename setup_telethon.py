#!/usr/bin/env python3
"""
Авторизация Telethon.
api_id   = 39578814 — стабильный идентификатор клиента (Telegram Desktop).
Это не меняет чей аккаунт — вход всё равно через твой номер телефона.
"""
import asyncio, os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

BASE    = os.path.dirname(os.path.abspath(__file__))
SESSION = os.path.join(BASE, "tg_user_session")

API_ID   = 39578814
API_HASH = "18f9ab304c0119a6ab28ff913f02f192"

async def main():
    phone = input("Введи номер телефона (напр. +79161234567): ").strip()

    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()

    result = await client.send_code_request(phone)
    print("✅ Код отправлен — проверь Telegram (сообщение от 'Telegram')")

    code = input("Введи код: ").strip()

    try:
        await client.sign_in(phone, code, phone_code_hash=result.phone_code_hash)
    except SessionPasswordNeededError:
        password = input("Введи пароль 2FA: ").strip()
        await client.sign_in(password=password)

    me = await client.get_me()
    print(f"\n✅ Авторизован: {me.first_name} (@{me.username})")
    await client.disconnect()

asyncio.run(main())
