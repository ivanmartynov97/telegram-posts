#!/usr/bin/env python3
"""
Локальный relay: слушает на localhost:19191
Принимает POST с полем "text", отправляет в Telegram канал.
Запускается автоматически через launchd.
"""

import http.server
import urllib.request
import urllib.parse
import json
import os
import logging
import sys

PORT = 19191
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "relay.log")

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def send_to_telegram(text: str) -> dict:
    cfg = load_config()
    url = f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": cfg["channel_id"],
        "text": text,
        "parse_mode": "HTML"
    }).encode()
    req = urllib.request.Request(url, data=data, method="POST",
                                  headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())

class RelayHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        params = urllib.parse.parse_qs(body)
        text = params.get("text", [""])[0]

        if not text:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"No text")
            return

        try:
            result = send_to_telegram(text)
            msg_id = result["result"]["message_id"]
            logging.info(f"Posted message_id={msg_id}: {text[:60]}...")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "message_id": msg_id}).encode())
        except Exception as e:
            logging.error(f"Failed: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def do_GET(self):
        """Health check"""
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Telegram relay OK")

    def log_message(self, fmt, *args):
        logging.info(fmt % args)

if __name__ == "__main__":
    logging.info(f"Starting relay on localhost:{PORT}")
    server = http.server.HTTPServer(("127.0.0.1", PORT), RelayHandler)
    logging.info("Relay ready")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Relay stopped")
        sys.exit(0)
