#!/bin/bash
cd "$(dirname "$0")"
/usr/bin/python3 diag_stuck.py 2>&1 | tee diag_stuck_output.txt
echo ""
read -p "Готово. Нажми Enter чтобы закрыть..."
