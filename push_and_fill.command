#!/bin/bash
cd "$(dirname "$0")"
export GROQ_KEY="$(python3 -c 'import json; d=json.load(open("config.json")); print(d.get("groq_key",""))' 2>/dev/null)"
OUT=/tmp/push_and_fill_output.txt
{
  echo "=== 1. Пуш кода (book-cover фикс, Идеи фикс, 2 новых канала) ==="
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git add index.html config.json ai_fill.py
  git commit -m "Fix book-cover image leak, merge strict+relaxed Идеи search, add channels 3-4 (facts theme)"
  git pull --rebase origin main
  git push origin main
  echo "PUSH_EXIT=$?"
  git log --oneline -1
  echo ""
  echo "=== 2. Проверка что index.html реально live на GitHub ==="
  LOCAL_SIZE=$(wc -c < index.html | tr -d ' ')
  curl -s "https://raw.githubusercontent.com/ivanmartynov97/telegram-posts/main/index.html?t=$(date +%s)" -o /tmp/live_index_check.html
  LIVE_SIZE=$(wc -c < /tmp/live_index_check.html | tr -d ' ')
  echo "Локальный размер: $LOCAL_SIZE / Live размер: $LIVE_SIZE"
  if [ "$LOCAL_SIZE" == "$LIVE_SIZE" ]; then echo "✅ СОВПАДАЕТ — фикс реально live"; else echo "❌ НЕ СОВПАДАЕТ"; fi
  echo ""
  echo "=== 3. AI-половина для queue (История+), 14 постов (history) ==="
  /usr/bin/python3 ai_fill.py 14 queue history
  echo ""
  echo "=== 4. AI-половина для queue2 (Рыцарь), 21 постов (history) ==="
  /usr/bin/python3 ai_fill.py 21 queue2 history
  echo ""
  echo "=== 5. Стартовое заполнение queue3 (Факт по секрету), 14 постов (facts) ==="
  /usr/bin/python3 ai_fill.py 14 queue3 facts
  echo ""
  echo "=== 6. Стартовое заполнение queue4 (Умная утка), 14 постов (facts) ==="
  /usr/bin/python3 ai_fill.py 14 queue4 facts
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/push_and_fill_output.txt"
unset GROQ_KEY
read -p "Готово. Нажми Enter чтобы закрыть..."
