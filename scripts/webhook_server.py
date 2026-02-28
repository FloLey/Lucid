#!/usr/bin/env python3
"""Webhook receiver for Gitea push events.

Listens on 127.0.0.1:WEBHOOK_PORT (default 9000).
On a valid POST /deploy for a push to main, runs scripts/deploy.sh
in the background and returns 200 immediately.

Configuration (environment variables):
  WEBHOOK_PORT    TCP port to listen on (default: 9000)
  WEBHOOK_SECRET  HMAC-SHA256 secret matching the Gitea webhook config.
                  If empty, signature verification is skipped (not recommended).
"""

import hashlib
import hmac
import json
import logging
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(os.environ.get("WEBHOOK_PORT", "9000"))
SECRET = os.environ.get("WEBHOOK_SECRET", "").encode()

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPLOY_SCRIPT = os.path.join(REPO_ROOT, "scripts", "deploy.sh")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/deploy":
            self._respond(404, b"not found")
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        if SECRET:
            sig = self.headers.get("X-Gitea-Signature", "")
            expected = hmac.new(SECRET, body, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, sig):
                log.warning("Invalid webhook signature — request rejected")
                self._respond(403, b"forbidden")
                return

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._respond(400, b"bad request")
            return

        ref = payload.get("ref", "")
        if ref != "refs/heads/main":
            log.info("Ignoring push to %s", ref)
            self._respond(200, b"ignored")
            return

        log.info("Push to main — launching deploy")
        subprocess.Popen(["/bin/bash", DEPLOY_SCRIPT])
        self._respond(200, b"deploying")

    def _respond(self, code: int, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:  # silence default access log
        pass


if __name__ == "__main__":
    if not SECRET:
        log.warning("WEBHOOK_SECRET is not set — signature verification disabled")

    server = HTTPServer(("127.0.0.1", PORT), WebhookHandler)
    log.info("Listening on 127.0.0.1:%d/deploy", PORT)
    server.serve_forever()
