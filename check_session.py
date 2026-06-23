#!/usr/bin/env python3
import asyncio, os, sys

BASE    = os.path.dirname(os.path.abspath(__file__))
SESSION = os.path.join(BASE, "tg_user_session")
API_ID   = 39578814
API_HASH = "18f9ab304c0119a6ab28ff913f02f192"

print(f"Папка: {BASE}")
print(f"Сессия: {SESSION}.session")

sess_file = SESSION + ".session"
if os.path.exists(sess_file):
    size = os.path.getsize(sess_file)
    print(f"✅ Файл сессии найден: {size} байт")
else:
    print("❌ Файл сессии НЕ найден!")
    sys.exit(1)

from telethon import TelegramClient

async def main():
    client = TelegramClient(SESSION, API_ID, API_HASH)
    print("Подключаюсь...")
    await client.connect()
    print(f"Подключён: {client.is_connected()}")

    try:
        me = await client.get_me()
        if me:
            print(f"\n✅ Авторизован: {me.first_name} (@{me.username})")
            print("\nЗапускаю early_performance.py...")
            await client.disconnect()
            os.system(f"python3 '{os.path.join(BASE, 'early_performance.py')}'")
            print("\nПушу в GitHub...")
            os.chdir(BASE)
            os.system("git add -A && git push origin main")
            print("\nУстанавливаю launchd агент...")
            plist = os.path.join(BASE, "com.ivan.early-performance.plist")
            if os.path.exists(plist):
                os.system(f"cp '{plist}' ~/Library/LaunchAgents/")
                os.system("launchctl unload ~/Library/LaunchAgents/com.ivan.early-performance.plist 2>/dev/null")
                os.system("launchctl load ~/Library/LaunchAgents/com.ivan.early-performance.plist")
                print("✅ Агент запущен! early_performance будет работать каждые 5 минут.")
            else:
                print("⚠️  plist не найден")
        else:
            print("\n❌ get_me() вернул None")
    except Exception as e:
        print(f"\n❌ Ошибка: {type(e).__name__}: {e}")
        print("\nСессия устарела или была отозвана. Запусти qr_login.command снова.")
    finally:
        if client.is_connected():
            await client.disconnect()

asyncio.run(main())
