#!/bin/bash
cd "$(dirname "$0")"
python3 fix_subscriber_history.py
read -p "Нажми Enter чтобы закрыть..."
