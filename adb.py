import cgi
import os
import json
import subprocess
import threading
import time
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from PIL import Image
import cv2
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(description="VNC Control Server")
    parser.add_argument("--host", type=str, required=True,
                        help="Host for the HTTP server")
    parser.add_argument("--port", type=int, required=True,
                        help="Port for the HTTP server")
    parser.add_argument("--device", type=str, required=True,
                        help="ADB device name")
    parser.add_argument("--frac", type=float, required=False, default="0.5",
                        help="Fractured screen resolution")
    return parser.parse_args()

def create_snapshot_dir(snapshot_dir):
    if not os.path.exists(snapshot_dir):
        os.makedirs(snapshot_dir)


class AutoJSHandler(BaseHTTPRequestHandler):
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
                screen_height /= args.frac
                screen_width /= args.frac

            x = int(fractional_x * screen_width)
            y = int(fractional_y * screen_height)
            print(f'Control input: x={x}, y={y}')

            # Send mouse move and click input using vncdotool
            subprocess.run(['./autojs.sh', args.device, 'tap', str(x), str(y)])

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
            subprocess.run(['./autojs.sh', args.device, 'text', text])

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"message": "Text input sent successfully"}')

        elif self.path == '/unlock':
            subprocess.run(['./autojs.sh', args.device, 'unlock'])

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"message": "Unlock command sent successfully"}')

        elif self.path == '/save_image':
            ctype, pdict = cgi.parse_header(self.headers.get('content-type'))
            pdict['boundary'] = bytes(pdict['boundary'], "utf-8")

            print(ctype)

            if ctype == 'multipart/form-data':
                # Read the request body as multipart form data
                fields = cgi.parse_multipart(self.rfile, pdict)
                image_data = fields.get('file')[0]
                image_name = fields.get('name')[0]
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error": "Invalid request content type"}')
                return


            # # Save image to the snapshots directory with timestamp
            image_path = os.path.join(SNAPSHOT_DIR, image_name)
            with open(image_path, 'wb') as file:
                file.write(image_data)

            subprocess.run(['./autojs.sh', args.device, 'save_image', image_path])

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"message": "Image received successfully"}')


def calculate_similarity(frame1, frame2):
    # Convert frames to grayscale
    frame1 = cv2.imread(frame1)
    frame2 = cv2.imread(frame2)
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY).astype(np.float32)

    # Ensure both images have the same size
    if gray1.shape != gray2.shape:
        height, width = gray1.shape
        gray2 = cv2.resize(gray2, (width, height))

    # Calculate structural similarity index
    similarity = cv2.compareHist(gray1, gray2, cv2.HISTCMP_CORREL)

    return similarity

def capture_autojs():
    while True:
        snapshot_path = os.path.join(SNAPSHOT_DIR, 'snapshot-stack.png')
        subprocess.run(['./autojs.sh', args.device,
                       'screenshoot', snapshot_path])
        try:
            # resize image to 0.5
            img = cv2.imread(snapshot_path)
            img = cv2.resize(img, (0, 0), fx=args.frac, fy=args.frac)
            cv2.imwrite(snapshot_path, img)
            if calculate_similarity(snapshot_path, os.path.join(SNAPSHOT_DIR, 'snapshot.png')) < 0.9:
                os.rename(snapshot_path, os.path.join(SNAPSHOT_DIR, 'snapshot.png'))
        except Exception as e:
            # print(f'Error: {e}')
            pass
        time.sleep(INTERVAL)

def push_autojs():
    subprocess.run(['./autojs.sh', args.device, 'push'])


def run(server_class=HTTPServer, handler_class=AutoJSHandler, host='0.0.0.0', port=35981):
    server_address = (host, port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting httpd server on {host}:{port}')
    httpd.serve_forever()


if __name__ == '__main__':
    args = parse_args()
    SNAPSHOT_DIR = 'snapshots'
    INTERVAL = 3  # Capture interval in seconds
    create_snapshot_dir(SNAPSHOT_DIR)
    push_autojs()
    threading.Thread(target=capture_autojs).start()
    run(host=args.host, port=args.port)
