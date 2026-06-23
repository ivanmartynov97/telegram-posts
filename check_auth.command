#!/bin/bash
cd "$(dirname "$0")"
OUT=/tmp/check_auth_output.txt
{
  /usr/bin/python3 -c "
import asyncio
from telethon import TelegramClient
API_ID = 39578814
API_HASH = '18f9ab304c0119a6ab28ff913f02f192'
async def main():
    client = TelegramClient('tg_user_session', API_ID, API_HASH)
    await client.connect()
    ok = await client.is_user_authorized()
    print('AUTHORIZED:', ok)
    if ok:
        me = await client.get_me()
        print('Logged in as:', me.first_name, me.username)
    await client.disconnect()
asyncio.run(main())
"
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/check_auth_output.txt"
read -p "Готово. Нажми Enter чтобы закрыть..."
