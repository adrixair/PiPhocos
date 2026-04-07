from __future__ import annotations

import argparse
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class MockRedirectHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def _redirect_to_mock(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", "/?mock=1")
            self.end_headers()
            return True
        return False

    def do_GET(self):
        if self._redirect_to_mock():
            return
        super().do_GET()

    def do_HEAD(self):
        if self._redirect_to_mock():
            return
        super().do_HEAD()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=4173)
    parser.add_argument("--directory", default="site")
    args = parser.parse_args()

    handler = partial(MockRedirectHandler, directory=args.directory)
    server = ThreadingHTTPServer(("0.0.0.0", args.port), handler)
    print(f"Serving UI mock on http://127.0.0.1:{args.port}/?mock=1")
    server.serve_forever()


if __name__ == "__main__":
    main()
