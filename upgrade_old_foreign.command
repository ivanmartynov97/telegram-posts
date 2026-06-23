#!/bin/bash
cd "$(dirname "$0")"
python3 upgrade_old_foreign.py
read -p "Нажми Enter чтобы закрыть..."
