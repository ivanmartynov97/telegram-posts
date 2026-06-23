#!/bin/bash
# Мастер-скрипт:
# 1. Удаляет плохие AI-посты из queue (history+)
# 2. Генерирует 14 постов для queue2 (Рыцарь, история)
# 3. Генерирует 14 постов для queue3 (Факт по секрету, факты, мультяшные картинки)
# 4. Генерирует 14 постов для queue4 (Умная утка, факты, кино-картинки + Кря!)
cd "$(dirname "$0")"
OUT=/tmp/master_fill_output.txt
GROQ_KEY="$(python3 -c 'import json; d=json.load(open("config.json")); print(d.get("groq_key",""))' 2>/dev/null)"
OPENROUTER_KEY="$(python3 -c 'import json; d=json.load(open("config.json")); print(d.get("openrouter_key",""))' 2>/dev/null)"
GH_TOKEN=$(python3 -c "import json; print(json.load(open('config.json'))['github_token'])")
REPO="ivanmartynov97/telegram-posts"

{
  # ── 0. Пушим обновлённый ai_fill.py (строгий is_relevant, новый Groq ключ) ──
  rm -f .git/HEAD.lock .git/index.lock 2>/dev/null
  git add ai_fill.py
  git commit -m "Fix: строгий is_relevant для картинок + новый Groq ключ" || echo "(нечего пушить)"
  git pull --rebase origin main
  git push origin main
  echo "=== PUSH_EXIT=$? ==="

  # ── 1. Удаляем плохие AI-посты из queue (history+) ─────────────────────────
  echo ""
  echo "=== Чистим плохие AI-посты из queue (history+) ==="
  API="https://api.github.com/repos/$REPO/contents/queue"
  FILES=$(curl -s -H "Authorization: token $GH_TOKEN" "$API" | python3 -c "
import sys,json
files = json.load(sys.stdin)
if isinstance(files, list):
    for f in files:
        if f['name'].endswith('.json'):
            print(f['name'], f['sha'], f['download_url'])
" 2>/dev/null)

  DELETED=0
  KEPT=0
  while IFS=' ' read -r filename sha download_url; do
    [ -z "$filename" ] && continue
    CONTENT=$(curl -s "$download_url")
    FROM_AI=$(echo "$CONTENT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('from_ai', False))" 2>/dev/null)
    if [ "$FROM_AI" = "True" ] || [ "$FROM_AI" = "true" ]; then
      curl -s -X DELETE \
        -H "Authorization: token $GH_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"message\": \"Remove bad AI post: $filename\", \"sha\": \"$sha\"}" \
        "$API/$filename" > /dev/null
      echo "  🗑️  Удалён AI-пост: $filename"
      DELETED=$((DELETED + 1))
    else
      KEPT=$((KEPT + 1))
    fi
  done <<< "$FILES"
  echo "Удалено AI-постов: $DELETED, оставлено грабли: $KEPT"

  # ── 2. Генерируем новые посты ────────────────────────────────────────────────
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

cp "$OUT" "$(dirname "$0")/master_fill_output.txt"
read -p "Готово. Нажми Enter чтобы закрыть..."
