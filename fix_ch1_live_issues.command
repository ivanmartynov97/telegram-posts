#!/bin/bash
cd "$(dirname "$0")"
/usr/bin/python3 fix_ch1_live_issues.py 2>&1 | tee fix_ch1_live_issues_output.txt
echo ""
read -p "Готово. Нажми Enter чтобы закрыть..."
