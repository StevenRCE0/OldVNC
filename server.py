import os
import json
import threading
import time
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from vncdotool import api
from PIL import Image


def parse_args():
    parser = argparse.ArgumentParser(description="VNC Control Server")
    parser.add_argument("--host", type=str, required=True,
                        help="Host for the HTTP server")
    parser.add_argument("--port", type=int, required=True,
                        help="Port for the HTTP server")
    parser.add_argument("--vnc_host", type=str,
                        required=True, help="VNC server host")
    parser.add_argument("--vnc_port", type=int,
                        required=True, help="VNC server port")
    parser.add_argument("--vnc_password", type=str,
                        required=True, help="VNC server password")
    return parser.parse_args()


def connect_vnc(vnc_host, vnc_port, vnc_password):
    return api.connect(f'{vnc_host}::{vnc_port}', password=vnc_password)


def create_snapshot_dir(snapshot_dir):
    if not os.path.exists(snapshot_dir):
        os.makedirs(snapshot_dir)


class VNCHandler(BaseHTTPRequestHandler):
    is_capturing = False

    def log_message(self, format: str, *args) -> None:
        return

    def do_GET(self):
        if self.path.startswith('/snapshot.png'):
            snapshot_path = os.path.join(SNAPSHOT_DIR, 'snapshot.png')
            if os.path.exists(snapshot_path):
                self.send_response(200)
                self.send_header('Content-type', 'image/png')
                self.end_headers()
                with open(snapshot_path, 'rb') as file:
                    self.wfile.write(file.read())
            else:
                self.send_response(404)
                self.end_headers()
        else:
            if self.path == '/':
                self.path = '/index.html'
            try:
                file_path = os.path.join('static', self.path.lstrip('/'))
                with open(file_path, 'rb') as file:
                    self.send_response(200)
                    if file_path.endswith('.html'):
                        self.send_header('Content-type', 'text/html')
                    elif file_path.endswith('.js'):
                        self.send_header(
                            'Content-type', 'application/javascript')
                    elif file_path.endswith('.css'):
                        self.send_header('Content-type', 'text/css')
                    self.end_headers()
                    self.wfile.write(file.read())
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()

    def do_POST(self):
        if self.path == '/control':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            fractional_x = data.get('x')
            fractional_y = data.get('y')
            if fractional_x is None or fractional_y is None:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error": "Invalid control input"}')
                return

            # Read the screen dimensions from the snapshot image
            snapshot_path = os.path.join(SNAPSHOT_DIR, 'snapshot.png')
            if not os.path.exists(snapshot_path):
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b'{"error": "Snapshot not found"}')
                return

            with Image.open(snapshot_path) as img:
                screen_width, screen_height = img.size

            x = int(fractional_x * screen_width)
            y = int(fractional_y * screen_height)
            print(f'Control input: x={x}, y={y}')

            # Send mouse move and click input using vncdotool
            client.mouseMove(x, y)
            client.mousePress(1)

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"message": "Control input sent successfully"}')

        elif self.path == '/send_string':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            text = data.get('text')
            if text is None:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error": "Invalid text input"}')
                return

            # Send string input using vncdotool
            print(f'Sending text: {text.encode().decode()}')
            client.paste(text.encode().decode())

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"message": "Text input sent successfully"}')


def capture_vnc():
    while True:
        if not VNCHandler.is_capturing:
            VNCHandler.is_capturing = True
            snapshot_path = os.path.join(SNAPSHOT_DIR, 'snapshot.png')
            client.captureScreen(snapshot_path)
            VNCHandler.is_capturing = False
        time.sleep(INTERVAL)


def run(server_class=HTTPServer, handler_class=VNCHandler, host='0.0.0.0', port=35981):
    server_address = (host, port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on {host}:{port}')
    httpd.serve_forever()


if __name__ == '__main__':
    args = parse_args()
    SNAPSHOT_DIR = 'snapshots'
    INTERVAL = 1  # Capture interval in seconds

    create_snapshot_dir(SNAPSHOT_DIR)
    client = connect_vnc(args.vnc_host, args.vnc_port, args.vnc_password)

    threading.Thread(target=capture_vnc).start()
    run(host=args.host, port=args.port)
