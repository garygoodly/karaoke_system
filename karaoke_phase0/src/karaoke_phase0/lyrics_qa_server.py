"""Loopback-only, allowlisted audio/HTML server for Lyrics QA."""
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def start_preview_server(page, vocals):
    page, vocals = Path(page).resolve(), Path(vocals).resolve()
    if not page.is_file() or not vocals.is_file():
        raise FileNotFoundError('Lyrics QA HTML and generated/vocals.wav must exist')

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            route = urlsplit(self.path).path
            if route not in ('/', '/vocals.wav'):
                self.send_error(404)
                return
            path = page if route == '/' else vocals
            content_type = 'text/html; charset=utf-8' if route == '/' else 'audio/wav'
            size = path.stat().st_size
            range_header = self.headers.get('Range', '')
            start, end = 0, size - 1
            if range_header.startswith('bytes='):
                try:
                    spec = range_header[6:]
                    first, last = spec.split('-', 1)
                    if not first:
                        count = int(last)
                        if count <= 0: raise ValueError()
                        start = max(0, size - count)
                    else:
                        start = int(first)
                        if last: end = min(int(last), size - 1)
                    if start < 0 or start >= size or end < start: raise ValueError()
                except (ValueError, OverflowError):
                    self.send_response(416)
                    self.send_header('Content-Range', f'bytes */{size}')
                    self.end_headers()
                    return
                self.send_response(206)
                self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
            else:
                self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(end-start+1))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            try:
                with path.open('rb') as f:
                    f.seek(start)
                    remaining = end-start+1
                    while remaining:
                        chunk = f.read(min(65536, remaining))
                        if not chunk: break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *args):
            pass

    server = _Server(('127.0.0.1', 0), Handler)
    Thread(target=server.serve_forever, daemon=True, name='lyrics-qa-http').start()
    return server, f'http://127.0.0.1:{server.server_port}/'
