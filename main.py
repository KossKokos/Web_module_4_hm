from http.server import HTTPServer, BaseHTTPRequestHandler
import pathlib
import urllib.parse
import mimetypes
import json
import socket
import logging
from threading import Thread
from datetime import datetime


BASE_DIR = pathlib.Path()
STATUS_200 = 200
STATUS_302 = 302
STATUS_404 = 404
IP = '127.0.0.1'
PORT_3000 = 3000
PORT_5000 = 5000
DATA_BYTES = 1024


def send_data_to_socket(data):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.sendto(data, (IP, PORT_5000))
    client_socket.close()

class HTTPHandler(BaseHTTPRequestHandler):
    
    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-Length']))
        send_data_to_socket(body)

        self.send_response(STATUS_302)
        self.send_header('Location', '/message.html')
        self.end_headers()
    
    def do_GET(self):
        way = urllib.parse.urlparse(self.path)
        match way.path:
            case "/":
                self.write_html('index.html')
            case "/message.html":
                self.write_html('message.html')
            case _:
                print(BASE_DIR / way.path[1:])
                file = BASE_DIR / way.path[1:]
                if file.exists():
                    self.write_css_png(file)
                else:
                    self.write_html('error.html', STATUS_404)
                
    def write_html(self, file, status=STATUS_200):
        self.send_response(status)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()

        with open(file, 'rb') as f:
            self.wfile.write(f.read())

    def write_css_png(self, file, status=STATUS_200):
        self.send_response(status)
        mime_t, x = mimetypes.guess_type(file)
        if mime_t:
            self.send_header('Content-Type', mime_t)
        else:
            self.send_header('Content-Type', 'text/plain')
        self.end_headers()

        with open(file, 'rb') as f:
            self.wfile.write(f.read())


def run(server=HTTPServer, handler=HTTPHandler):
    address = ('0.0.0.0', PORT_3000)
    http_server = server(address, handler)
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()


def save_data(body):
    body = urllib.parse.unquote_plus(body.decode())
    try:
        dct_json = {key: value for key, value in [el.split('=') for el in body.split('&')]}
        date_now = datetime.now()

        with open('storage/data.json', 'r', encoding='utf-8') as f:
            info = json.load(f)
            info.update({str(date_now): dct_json})

        with open('storage/data.json', 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False)

    except ValueError as err:
        logging.error(f'Failed to parse {body} because of error: {err}')
        
    except OSError:
        logging.error(f'Failed to write {body} because of error: {err}')


def run_socket(ip, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = (ip, port)
    server_socket.bind(server)
    try:
        while True:
            data, address = server_socket.recvfrom(DATA_BYTES)
            save_data(data)
    except KeyboardInterrupt:
        logging.info('Socket server stopped')
    finally:
        server_socket.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(threadName)s - %(message)s')
    database_dir = pathlib.Path().joinpath('storage')
    database_file = database_dir / 'data.json'
    if not database_file.exists():
        with open(database_file, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False)

    thread_server = Thread(target=run)
    thread_server.start()

    thread_socket = Thread(target=run_socket(IP, PORT_5000))
    thread_socket.start()
