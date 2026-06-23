#!/bin/bash
cd "$(dirname "$0")"
python3 clean_foreign_no_image.py
read -p "Нажми Enter чтобы закрыть..."
