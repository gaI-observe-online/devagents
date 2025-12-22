## Notifications regression evidence — 2025-12-22

### Goal

Demonstrate that daily digest flushing can run end-to-end (queue → flush) without external services by using a local webhook receiver.

### Commands run (verbatim) + outputs (verbatim)

```bash
# Seed one digest event to /tmp and flush it via a local HTTP server that accepts POST.
bash -lc "rm -f /tmp/gados_digest.jsonl; python3 -c 'from app.notifications import NotificationEvent, enqueue_digest_event; enqueue_digest_event(NotificationEvent(event_type=\"qa.digest.seed\", priority=\"normal\", summary=\"seed\"), store_path=\"/tmp/gados_digest.jsonl\")'; python3 - <<'PY'
import os, subprocess, threading, time
from http.server import BaseHTTPRequestHandler, HTTPServer

class H(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get('Content-Length', '0'))
        _ = self.rfile.read(n)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'ok')

    def log_message(self, format, *args):
        return

s = HTTPServer(('127.0.0.1', 9999), H)
t = threading.Thread(target=s.serve_forever, daemon=True)
t.start()
time.sleep(0.2)
os.environ['GADOS_WEBHOOK_URL'] = 'http://127.0.0.1:9999'
os.environ['GADOS_DIGEST_STORE_PATH'] = '/tmp/gados_digest.jsonl'
r = subprocess.run(['python3', 'scripts/flush_digest.py'], capture_output=True, text=True)
print(r.stdout, end='')
print(r.stderr, end='')
s.shutdown(); s.server_close()
raise SystemExit(r.returncode)
PY"
shipped_digest_events=1
```

