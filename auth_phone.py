#!/usr/bin/env python3
"""
Авторизация через номер телефона.
Код придёт в Telegram-приложение (как обычное сообщение от Telegram).
"""
import asyncio, os

BASE    = os.path.dirname(os.path.abspath(__file__))
SESSION = os.path.join(BASE, "tg_user_session")
API_ID   = 39578814
API_HASH = "18f9ab304c0119a6ab28ff913f02f192"

from telethon import TelegramClient

async def main():
    # Удаляем старую сессию
    for ext in [".session", ".session-journal"]:
        p = SESSION + ext
        if os.path.exists(p):
            os.remove(p)
            print(f"Удалена: {p}")

    client = TelegramClient(SESSION, API_ID, API_HASH)

    print("\n" + "="*50)
    print("ВХОД В TELEGRAM ЧЕРЕЗ НОМЕР ТЕЛЕФОНА")
    print("="*50)
    print("Код придёт в Telegram как сообщение от 'Telegram'")
    print("Если есть облачный пароль — спросим его тоже\n")

    await client.start(
        phone=lambda: input("Номер телефона (+37xxxxxxxx): "),
        code_callback=lambda: input("Код из Telegram: "),
        password=lambda: input("Облачный пароль (если есть): "),
    )

    me = await client.get_me()
    print(f"\n✅ Авторизован: {me.first_name} (@{me.username})")
    print(f"Сессия: {SESSION}.session")
    print("\nТеперь запусти check_session.command")

    await client.disconnect()

asyncio.run(main())
