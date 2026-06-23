#!/bin/bash
# Удаляет все AI-сгенерированные посты из queue (history_plus_facts).
# Грабли-посты (from_ai=false или отсутствует) остаются нетронутыми.
cd "$(dirname "$0")"

GH_TOKEN=$(python3 -c "import json; print(json.load(open('config.json'))['github_token'])")
REPO="ivanmartynov97/telegram-posts"
QUEUE_DIR="queue"
API="https://api.github.com/repos/$REPO/contents/$QUEUE_DIR"

echo "=== Получаем список постов в queue ==="
FILES=$(curl -s -H "Authorization: token $GH_TOKEN" "$API" | python3 -c "
import sys,json
files = json.load(sys.stdin)
if isinstance(files, list):
    for f in files:
        if f['name'].endswith('.json'):
            print(f['name'], f['sha'], f['download_url'])
" 2>/dev/null)

if [ -z "$FILES" ]; then
    echo "Нет файлов в очереди или ошибка доступа"
    read -p "Нажми Enter..."
    exit 1
fi

TOTAL=0
DELETED=0
KEPT=0

echo ""
echo "=== Проверяем каждый пост ==="
while IFS=' ' read -r filename sha download_url; do
    [ -z "$filename" ] && continue
    TOTAL=$((TOTAL + 1))

    # Загружаем содержимое поста
    CONTENT=$(curl -s "$download_url")
    FROM_AI=$(echo "$CONTENT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('from_ai', False))" 2>/dev/null)

    if [ "$FROM_AI" = "True" ] || [ "$FROM_AI" = "true" ]; then
        # AI пост — удаляем
        TEXT_PREVIEW=$(echo "$CONTENT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('text','')[:60])" 2>/dev/null)
        echo "  🗑️  Удаляем AI-пост: $filename"
        echo "     Текст: $TEXT_PREVIEW..."

        DEL_RESP=$(curl -s -X DELETE \
            -H "Authorization: token $GH_TOKEN" \
            -H "Content-Type: application/json" \
            -d "{\"message\": \"Remove bad AI post: $filename\", \"sha\": \"$sha\"}" \
            "$API/$filename")

        if echo "$DEL_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if 'commit' in d else 1)" 2>/dev/null; then
            echo "     ✅ Удалён"
            DELETED=$((DELETED + 1))
        else
            echo "     ❌ Ошибка: $(echo "$DEL_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('message','?'))" 2>/dev/null)"
        fi
    else
        echo "  ✅ Оставляем (грабли): $filename"
        KEPT=$((KEPT + 1))
    fi
done <<< "$FILES"

echo ""
echo "=== ГОТОВО ==="
echo "Всего постов: $TOTAL"
echo "Удалено AI-постов: $DELETED"
echo "Оставлено (грабли): $KEPT"
read -p "Нажми Enter чтобы закрыть..."
