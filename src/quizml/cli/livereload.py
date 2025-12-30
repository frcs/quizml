import http.server
import socketserver
import threading
import json
import socket
import time
from quizml.cli.errorhandler import print_error

# Global state for the LiveReload server
LIVERELOAD_PORT = None
LIVERELOAD_TIMESTAMP = 0.0
SERVER_THREAD = None

class LiveReloadHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # Silence logs

    def do_GET(self):
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            data = json.dumps({'timestamp': LIVERELOAD_TIMESTAMP})
            self.wfile.write(data.encode())
        else:
            self.send_error(404)

def start_livereload_server():
    global LIVERELOAD_PORT, SERVER_THREAD
    if SERVER_THREAD is not None:
        return

    # Find a free port
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            LIVERELOAD_PORT = s.getsockname()[1]

        def run_server():
            # Allow address reuse to prevent issues if we restart quickly
            socketserver.TCPServer.allow_reuse_address = True
            with socketserver.TCPServer(("", LIVERELOAD_PORT), LiveReloadHandler) as httpd:
                httpd.serve_forever()

        SERVER_THREAD = threading.Thread(target=run_server, daemon=True)
        SERVER_THREAD.start()
        # print(f"[dim]LiveReload server started on port {LIVERELOAD_PORT}[/dim]")
    except Exception as e:
        print_error(f"Failed to start LiveReload server: {e}", title="Warning")

def update_timestamp():
    global LIVERELOAD_TIMESTAMP
    LIVERELOAD_TIMESTAMP = time.time()

def get_livereload_port():
    return LIVERELOAD_PORT
