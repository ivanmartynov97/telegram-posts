#!/usr/bin/env python3
"""
Собирает реакции на посты канала через Telegram Bot API getUpdates.
Запускается каждый час через launchd.
Сохраняет данные в GitHub analytics/{message_id}.json
"""

import json, os, ssl, base64, logging
import urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

BASE         = os.path.dirname(os.path.abspath(__file__))
CONFIG       = os.path.join(BASE, "config.json")
LOG_PATH     = os.path.join(BASE, "fetch_reactions.log")
OFFSET_FILE  = os.path.join(BASE, "analytics_offset.txt")
GH_REPO      = "ivanmartynov97/telegram-posts"

logging.basicConfig(filename=LOG_PATH, level=logging.INFO,
                    format="%(asctime)s %(message)s")

def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def api_get(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        return json.loads(r.read())

def api_post(url, payload: dict):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST",
          headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        return json.loads(r.read())

def gh_get(gh_token, path):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    req = urllib.request.Request(url,
          headers={"Authorization": f"token {gh_token}",
                   "Accept": "application/vnd.github.v3+json"})
    with urllib.request.urlopen(req, timeout=10, context=ssl_ctx()) as r:
        return json.loads(r.read())

def gh_put(gh_token, path, content_str: str, sha: str = None, msg: str = "Update"):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    content = base64.b64encode(content_str.encode()).decode()
    payload = {"message": msg, "content": content}
    if sha:
        payload["sha"] = sha
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="PUT",
          headers={"Authorization": f"token {gh_token}",
                   "Accept": "application/vnd.github.v3+json",
                   "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10, context=ssl_ctx()) as r:
        return json.loads(r.read())

def load_offset():
    if os.path.exists(OFFSET_FILE):
        try:
            return int(open(OFFSET_FILE).read().strip())
        except:
            pass
    return 0

def save_offset(offset):
    with open(OFFSET_FILE, "w") as f:
        f.write(str(offset))

def update_analytics_record(gh_token, message_id: int, reactions: dict):
    """Загружает существующую запись из GitHub и обновляет реакции."""
    path = f"analytics/{message_id}.json"
    now_str = datetime.now(timezone(timedelta(hours=3))).isoformat()
    try:
        info = gh_get(gh_token, path)
        existing = json.loads(base64.b64decode(info["content"]).decode())
        existing["reactions"] = reactions
        existing["total_reactions"] = sum(reactions.values())
        existing["reactions_updated_at"] = now_str
        gh_put(gh_token, path, json.dumps(existing, ensure_ascii=False, indent=2),
               sha=info["sha"], msg=f"Reactions update: {message_id}")
        logging.info(f"Обновлены реакции для msg {message_id}: {reactions}")
    except Exception as e:
        logging.warning(f"Не удалось обновить analytics для {message_id}: {e}")

def main():
    with open(CONFIG) as f:
        cfg = json.load(f)
    token    = cfg["bot_token"]
    gh_token = cfg.get("github_token", "")

    if not gh_token:
        logging.error("github_token не задан в config.json")
        print("Ошибка: добавь github_token в config.json")
        return

    offset = load_offset()
    logging.info(f"Старт. Offset: {offset}")
    print(f"Старт. Offset: {offset}")

    # Получаем обновления реакций
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    params = {
        "offset": offset,
        "timeout": 5,
        "allowed_updates": ["message_reaction_count"]
    }
    try:
        res = api_post(url, params)
    except Exception as e:
        logging.error(f"getUpdates ошибка: {e}")
        print(f"Ошибка getUpdates: {e}")
        return

    if not res.get("ok"):
        logging.error(f"getUpdates вернул: {res}")
        return

    updates = res.get("result", [])
    logging.info(f"Получено {len(updates)} обновлений реакций")
    print(f"Получено {len(updates)} обновлений реакций")

    processed = 0
    for upd in updates:
        new_offset = upd["update_id"] + 1
        if new_offset > offset:
            offset = new_offset

        rc = upd.get("message_reaction_count")
        if not rc:
            continue

        message_id = rc.get("message_id")
        if not message_id:
            continue

        # Парсим реакции
        reactions = {}
        for r in rc.get("reactions", []):
            rtype = r.get("type", {})
            if rtype.get("type") == "emoji":
                emoji = rtype.get("emoji", "?")
                reactions[emoji] = r.get("total_count", 0)

        if reactions:
            update_analytics_record(gh_token, message_id, reactions)
            processed += 1

    save_offset(offset)
    logging.info(f"Обработано: {processed}. Новый offset: {offset}")
    print(f"Обработано: {processed}. Offset сохранён: {offset}")

if __name__ == "__main__":
    main()
