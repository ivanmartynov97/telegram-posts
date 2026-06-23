#!/bin/bash
# Удаляет все AI-посты из queue2 и генерирует 14 свежих с исправленным ai_fill.py
cd "$(dirname "$0")"
GROQ_KEY="$(python3 -c 'import json; d=json.load(open("config.json")); print(d.get("groq_key",""))' 2>/dev/null)"
OPENROUTER_KEY="$(python3 -c 'import json; d=json.load(open("config.json")); print(d.get("openrouter_key",""))' 2>/dev/null)"
GH_TOKEN=$(python3 -c "import json; print(json.load(open('config.json'))['github_token'])")
REPO="ivanmartynov97/telegram-posts"
API="https://api.github.com/repos/$REPO/contents/queue2"

{
  # Пушим фиксы
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git pull --rebase origin main 2>&1 | tail -3
  git push origin main 2>&1 | tail -3

  echo "=== Удаляем AI-посты из queue2 ==="
  FILES=$(curl -s -H "Authorization: token $GH_TOKEN" "$API" | python3 -c "
import sys,json
files = json.load(sys.stdin)
if isinstance(files, list):
    for f in files:
        if f['name'].endswith('.json'):
            print(f['name'], f['sha'], f['download_url'])
" 2>/dev/null)

  DELETED=0; KEPT=0
  while IFS=' ' read -r filename sha download_url; do
    [ -z "$filename" ] && continue
    CONTENT=$(curl -s "$download_url")
    FROM_AI=$(echo "$CONTENT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('from_ai', False))" 2>/dev/null)
    if [ "$FROM_AI" = "True" ] || [ "$FROM_AI" = "true" ]; then
      curl -s -X DELETE \
        -H "Authorization: token $GH_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"message\": \"Remove bad queue2 AI post: $filename\", \"sha\": \"$sha\"}" \
        "$API/$filename" > /dev/null
      echo "  🗑️  Удалён: $filename"
      DELETED=$((DELETED + 1))
    else
      echo "  ✅ Оставлен (грабли): $filename"
      KEPT=$((KEPT + 1))
    fi
  done <<< "$FILES"
  echo "Удалено: $DELETED, оставлено: $KEPT"

  echo ""
  echo "=== Генерируем Рыцарь (queue2, history, 14 постов) ==="
  GROQ_KEY="$GROQ_KEY" OPENROUTER_KEY="$OPENROUTER_KEY" python3 ai_fill.py 14 queue2 history

  echo ""
  echo "=== ГОТОВО ==="
} 2>&1 | tee /tmp/regen_queue2_output.txt
cp /tmp/regen_queue2_output.txt "$(dirname "$0")/regen_queue2_output.txt"
read -p "Готово. Enter чтобы закрыть..."
