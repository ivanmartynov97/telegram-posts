#!/bin/bash
cd "$(dirname "$0")"
git push origin main 2>&1
echo ""
read -p "Нажми Enter чтобы закрыть..."
