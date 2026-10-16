import http.server
import json
import socketserver
import threading
import time

from quizml.cli.errorhandler import print_error


class LiveReloadServer:
    """Own the server and timestamp used by one live-reload session."""

    def __init__(self):
        self.port = None
        self.timestamp = 0.0
        self._server = None
        self._thread = None

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return self.port

        owner = self

        class Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_GET(self):
                if self.path != "/status":
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                data = json.dumps({"timestamp": owner.timestamp})
                self.wfile.write(data.encode())

        class Server(socketserver.TCPServer):
            allow_reuse_address = True

        try:
            self._server = Server(("127.0.0.1", 0), Handler)
            self.port = self._server.server_address[1]
            self._thread = threading.Thread(
                target=self._server.serve_forever, daemon=True
            )
            self._thread.start()
            return self.port
        except OSError as err:
            print_error(f"Failed to start LiveReload server: {err}", title="Warning")
            self._server = None
            self.port = None
            return None

    def update_timestamp(self):
        self.timestamp = time.time()

    def stop(self):
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=1)
            self._thread = None
        self.port = None
