#!/bin/bash
cd "$(dirname "$0")"
OUT=/tmp/test_groq_output.txt
{
  /usr/bin/python3 -c "
import urllib.request, json, ssl
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
key = json.load(open('config.json')).get('groq_key','')
print('key length:', len(key))
body = json.dumps({'model':'llama-3.1-8b-instant','messages':[{'role':'user','content':'Скажи привет одним словом'}],'max_tokens':10}).encode()
req = urllib.request.Request('https://api.groq.com/openai/v1/chat/completions', data=body, method='POST',
    headers={'Authorization': f'Bearer {key}', 'Content-Type':'application/json'})
try:
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        print('STATUS:', r.status)
        print(r.read().decode())
except urllib.error.HTTPError as e:
    print('HTTP ERROR:', e.code)
    print(e.read().decode())
except Exception as e:
    print('OTHER ERROR:', repr(e))
"
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" "$(dirname "$0")/test_groq_output.txt"
read -p "Готово. Нажми Enter чтобы закрыть..."
