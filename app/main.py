import http.server
import socketserver
import socket
import datetime
from pymongo import MongoClient
from urllib.parse import parse_qs
from threading import Thread


HTTP_PORT = 3000
SOCKET_PORT = 5050
MONGO_URI = 'mongodb://localhost:27017/'


def save_to_mongodb(data):
    client = MongoClient(MONGO_URI)
    db = client.messages
    messages = db.messages
    messages.insert_one(data)


def socket_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind(('', SOCKET_PORT))
        server_socket.listen(1)
        print("Socket server listening on port", SOCKET_PORT)
        while True:
            client_socket, addr = server_socket.accept()
            with client_socket:
                while True:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    form_data = parse_qs(data.decode())
                    message_data = {
                        'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                        'username': form_data.get('username', [''])[0],
                        'message': form_data.get('message', [''])[0]
                    }
                    save_to_mongodb(message_data)


class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ['/', '/index.html']:
            self.path = 'app/index.html'
        elif self.path == '/message.html':
            self.path = 'app/message.html'
        else:
            self.path = 'app/error.html'
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path == '/message':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', SOCKET_PORT))
                sock.sendall(post_data)
                sock.close()
            self.send_response(302)
            self.end_headers()
        else:
            self.send_error(404, "File not found")


def main():
    thread = Thread(target=socket_server)
    thread.start()
    with socketserver.TCPServer(("", HTTP_PORT), MyHttpRequestHandler) as httpd:
        print("HTTP server serving at port", HTTP_PORT)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
