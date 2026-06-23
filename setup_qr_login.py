#!/usr/bin/env python3
"""
Авторизация Telethon через QR-код с поддержкой двухфакторной аутентификации.
Сканируй из Telegram: Настройки → Устройства → Подключить устройство.
"""
import asyncio, os, sys, base64

BASE    = os.path.dirname(os.path.abspath(__file__))
SESSION = os.path.join(BASE, "tg_user_session")
API_ID   = 39578814
API_HASH = "18f9ab304c0119a6ab28ff913f02f192"

try:
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError
except ImportError:
    print("Установка telethon...")
    os.system("pip3 install telethon --break-system-packages -q")
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError

def make_qr_terminal(url):
    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
    except Exception:
        print(f"URL: {url}")

async def main():
    # Удаляем старую сессию и любые lock-файлы
    for ext in [".session", ".session-journal", ".session-wal", ".session-shm"]:
        p = SESSION + ext
        if os.path.exists(p):
            os.remove(p)
            print(f"Удалена старая сессия: {p}")

    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()

    print("\n" + "="*50)
    print("QR-ВХОД В TELEGRAM (с поддержкой 2FA)")
    print("="*50)
    print("1. Открой Telegram на телефоне")
    print("2. Настройки → Устройства → Подключить устройство")
    print("3. Наведи камеру на QR\n")

    qr_login = await client.qr_login()
    make_qr_terminal(qr_login.url)
    print("\nСканируй QR. Жду...")

    authorized = False
    try:
        await qr_login.wait(60)
        authorized = True
    except SessionPasswordNeededError:
        print("\n🔐 У тебя включён облачный пароль Telegram (двухфакторка).")
        print("Введи пароль который ты установил в Telegram → Настройки → Конфиденциальность → Облачный пароль:")
        password = input("Пароль: ")
        await client.sign_in(password=password)
        authorized = True
    except asyncio.TimeoutError:
        print("\n❌ Время вышло (60 сек). Запусти снова и сканируй быстрее.")
        await client.disconnect()
        return

    if not authorized:
        print("\n❌ Авторизация не подтверждена.")
        await client.disconnect()
        return

    # Явно проверяем и сохраняем сессию на диск перед отключением
    is_auth = await client.is_user_authorized()
    print(f"is_user_authorized(): {is_auth}")

    me = await client.get_me()
    if me:
        print(f"✅ Авторизован: {me.first_name} (@{me.username})")
    else:
        print("⚠️ get_me() вернул None сразу после входа — это плохой знак")

    # Принудительно сохраняем сессию на диск
    try:
        client.session.save()
        print("💾 Сессия явно сохранена на диск (session.save())")
    except Exception as e:
        print(f"⚠️ Ошибка при сохранении сессии: {e}")

    await asyncio.sleep(1)  # даём время на флуш файловой системы
    await client.disconnect()
    print(f"\nРазмер файла сессии: {os.path.getsize(SESSION + '.session')} байт")
    print("Теперь запусти check_session.command — В ДРУГОМ окне терминала НЕ должно")
    print("быть других запущенных скриптов, использующих эту же сессию.")

asyncio.run(main())
