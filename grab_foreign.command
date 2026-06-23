#!/bin/bash
cd "$(dirname "$0")"
pip3 install telethon --break-system-packages -q 2>/dev/null
echo "Беру посты из чужих каналов..."
python3 grab_foreign.py
read -p "Нажми Enter чтобы закрыть..."
