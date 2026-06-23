#!/bin/bash
cd "$(dirname "$0")"
/usr/bin/python3 auto_publish.py 2>&1 | tee run_now_output.txt
echo ""
read -p "Готово. Нажми Enter чтобы закрыть..."
