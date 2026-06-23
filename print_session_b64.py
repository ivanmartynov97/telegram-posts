#!/usr/bin/env python3
"""Печатает Telethon-сессию в base64 — нужно скопировать в GitHub Secrets вручную."""
import base64, os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, "tg_user_session.session")

if not os.path.exists(path):
    print("❌ Файл сессии не найден. Сначала авторизуйся через qr_login.command")
else:
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    print("\n" + "="*60)
    print("Скопируй ВСЁ что между линиями (это секретный код твоей сессии,")
    print("вставь его ТОЛЬКО в поле секрета на GitHub, никуда больше):")
    print("="*60)
    print(b64)
    print("="*60)
