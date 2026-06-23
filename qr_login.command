#!/bin/bash
cd "$(dirname "$0")"
pip3 install telethon qrcode --break-system-packages -q 2>/dev/null
python3 setup_qr_login.py
read -p "Нажми Enter чтобы закрыть..."
