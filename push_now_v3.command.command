#!/bin/bash
cd "$(dirname "$0")"
pip3 install telethon --break-system-packages -q 2>/dev/null
python3 auth_phone.py
read -p "Нажми Enter чтобы закрыть..."
