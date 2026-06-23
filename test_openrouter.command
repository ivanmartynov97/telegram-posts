#!/bin/bash
cd "$(dirname "$0")"
OPENROUTER_KEY="$(python3 -c 'import json; d=json.load(open("config.json")); print(d.get("openrouter_key",""))' 2>/dev/null)"

echo "=== Проверяем рабочие бесплатные модели OpenRouter ==="
echo ""

# Список кандидатов для проверки
MODELS=(
  "meta-llama/llama-3.3-70b-instruct:free"
  "meta-llama/llama-3.1-405b-instruct:free"
  "meta-llama/llama-3.2-3b-instruct:free"
  "google/gemma-2-9b-it:free"
  "google/gemma-3-12b-it:free"
  "mistralai/mistral-small-3.1-24b-instruct:free"
  "deepseek/deepseek-r1:free"
  "deepseek/deepseek-v3-0324:free"
  "deepseek/deepseek-prover-v2:free"
  "qwen/qwen2.5-vl-7b-instruct:free"
  "qwen/qwen2.5-72b-instruct:free"
  "qwen/qwq-32b:free"
  "nousresearch/hermes-3-llama-3.1-405b:free"
  "microsoft/phi-4:free"
  "tngtech/deepseek-r1t-chimera:free"
  "moonshotai/kimi-k2:free"
  "openrouter/cypher-alpha:free"
)

for MODEL in "${MODELS[@]}"; do
  RESP=$(curl -s -o /tmp/or_test.txt -w "%{http_code}" \
    -X POST "https://openrouter.ai/api/v1/chat/completions" \
    -H "Authorization: Bearer $OPENROUTER_KEY" \
    -H "Content-Type: application/json" \
    -H "HTTP-Referer: https://ivanmartynov97.github.io" \
    -H "X-Title: test" \
    -d "{\"model\": \"$MODEL\", \"messages\": [{\"role\": \"user\", \"content\": \"Say hi\"}], \"max_tokens\": 10}")

  if [ "$RESP" = "200" ]; then
    echo "✅ РАБОТАЕТ: $MODEL"
  else
    ERR=$(cat /tmp/or_test.txt | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error',{}).get('message','?')[:60])" 2>/dev/null || echo "HTTP $RESP")
    echo "❌ $RESP — $MODEL — $ERR"
  fi
done

echo ""
echo "=== Готово ==="
read -p "Нажми Enter чтобы закрыть..."
