from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import mimetypes
import pathlib
import socket
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import datetime
import logging


BASE_DIR = pathlib.Path(__file__).parent
CHUNK_SIZE = 4096
HTTP_PORT = 8000
SOCKET_PORT = 5050
HTTP_HOST = "0.0.0.0"
SOCKET_HOST = "127.0.0.1"
DB_URI = "mongodb://mongodb:27017/"


class HttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == '/':
            self.send_html_file('index.html')
        elif pr_url.path == '/message':
            self.send_html_file('message.html')
        else:
            if pathlib.Path().joinpath(pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_html_file('error.html', 404)

    def do_POST(self):
        data = self.rfile.read(int(self.headers['Content-Length']))
        self.send_data_to_socket_server(data)

        data_parse = urllib.parse.unquote_plus(data.decode())
        data_dict = {key: value for key, value in [el.split('=') for el in data_parse.split('&')]}
        print(data_dict)

        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    def send_static(self):
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", 'text/plain')
        self.end_headers()
        with open(f'.{self.path}', 'rb') as file:
            self.wfile.write(file.read())

    def send_data_to_socket_server(self, data):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            server_address = (SOCKET_HOST, SOCKET_PORT)
            sock.sendto(data, server_address)
            sock.close()
        except socket.error:
            logging.error("Failed to send data")


def run_http_server():
    server_address = (HTTP_HOST, HTTP_PORT)
    http = HTTPServer(server_address, HttpHandler)
    try:
        http.serve_forever()
        logging.info(f"HTTP Sever started at {HTTP_HOST}:{HTTP_PORT}")
    except Exception as e:
        logging.error(e)
    finally:
        logging.info("Server stopped")
        http.server_close()


def save_to_db(data):
    # MongoDB connection
    client = MongoClient(DB_URI, server_api=ServerApi("1"))
    db = client['messages_db']
    collection = db['messages']
    try:
        data = urllib.parse.unquote_plus(data.decode())
        data_dict = {key: value for key, value in [el.split('=') for el in data.split('&')]}
        data_dict["date"] = str(datetime.datetime.now())
        collection.insert_one(data_dict)
        logging.info("Saved message to DB")
    except Exception as e:
        logging.error(e)
    finally:
        client.close()


def run_socket_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = (SOCKET_HOST, SOCKET_PORT)
    sock.bind(server_address)
    logging.info(f"Socket Server started at {SOCKET_HOST}:{SOCKET_PORT}")
    try:
        while True:
            data, address = sock.recvfrom(CHUNK_SIZE)
            logging.info(f"Received from {address}: {data.decode()}")
            save_to_db(data)
    except Exception as e:
        logging.info(e)
    finally:
        logging.info("Socket Server stopped")
        sock.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(threadName)s - %(message)s")
    from multiprocessing import Process

    Process(target=run_http_server, name="HTTP_Server").start()
    Process(target=run_socket_server, name="Socket_Server").start()
