#!/bin/bash
cd "$(dirname "$0")"
/usr/bin/python3 fix_foreign_leak_live.py 2>&1 | tee fix_foreign_leak_live_output.txt
echo ""
read -p "Готово. Нажми Enter чтобы закрыть..."
