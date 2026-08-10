import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/health", "/healthz"):
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Not Found")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        self.wfile.write(f"OK {now}\n".encode("utf-8"))

    def log_message(self, format, *args):
        return


def start_health_server(host: str = "0.0.0.0"):
    port_raw = os.getenv("PORT")
    if not port_raw:
        return None
    try:
        port = int(port_raw)
    except Exception:
        return None

    httpd = ThreadingHTTPServer((host, port), _Handler)

    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd
