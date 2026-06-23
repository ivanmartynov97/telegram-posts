#!/bin/bash
# Генерация постов на неделю:
#   queue2  — Рыцарь (@ricar_telegrama), исторические, 14 постов
#   queue3  — Факт по секрету (@fact_po_secretu), факты мультяшный стиль, 14 постов
#   queue4  — Умная утка (@umnaya_utka), факты кинематографический стиль + Кря!, 14 постов
cd "$(dirname "$0")"
OUT=/tmp/fill_week_output.txt

# ── Ключи ──────────────────────────────────────────────────────────────────
GROQ_KEY="$(python3 -c 'import json; d=json.load(open("config.json")); print(d.get("groq_key",""))' 2>/dev/null)"
OPENROUTER_KEY="$(python3 -c 'import json; d=json.load(open("config.json")); print(d.get("openrouter_key",""))' 2>/dev/null)"

{
  # Пушим обновлённые ai_fill.py и index.html (подпись Кря! + стиль картинок)
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git add ai_fill.py index.html
  git commit -m "Fix: расширить OpenRouter fallback модели + ускорить 429 retry"
  git pull --rebase origin main
  git push origin main
  echo "=== PUSH_EXIT=$? ==="

  echo ""
  echo "=== Генерируем Рыцарь (queue2, history, 14 постов) ==="
  GROQ_KEY="$GROQ_KEY" OPENROUTER_KEY="$OPENROUTER_KEY" python3 ai_fill.py 14 queue2 history

  echo ""
  echo "=== Генерируем Факт по секрету (queue3, facts, 14 постов) ==="
  GROQ_KEY="$GROQ_KEY" OPENROUTER_KEY="$OPENROUTER_KEY" python3 ai_fill.py 14 queue3 facts

  echo ""
  echo "=== Генерируем Умная утка (queue4, facts, 14 постов) ==="
  GROQ_KEY="$GROQ_KEY" OPENROUTER_KEY="$OPENROUTER_KEY" python3 ai_fill.py 14 queue4 facts

  echo ""
  echo "=== ВСЁ ГОТОВО ==="
} 2>&1 | tee "$OUT"

cp "$OUT" "$(dirname "$0")/fill_week_output.txt"
read -p "Готово. Нажми Enter чтобы закрыть..."
