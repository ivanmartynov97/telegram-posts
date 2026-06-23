#!/bin/bash
cd "$(dirname "$0")"
python3 reset_foreign_state.py
read -p "Нажми Enter чтобы закрыть..."
