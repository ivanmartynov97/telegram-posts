#!/bin/bash
cd "$(dirname "$0")"
python3 check_session.py
read -p "Нажми Enter чтобы закрыть..."
