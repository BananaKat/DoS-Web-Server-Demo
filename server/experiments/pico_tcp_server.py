#!/usr/bin/env python3
# Sets up a simple TCP server with the following assumptions:
# - We are using HTTP/1.1
# - No caching
# - No HTTPS (no encryption)
# - Only a single short-lived connection at a time
#   (no concurrent connections and connection closes after page is delivered)
# - Only HEAD & GET requests (static files only)
# Taken from:
# https://medium.com/@sakhawy/creating-an-http-server-from-scratch-ed41ef83314b
import socket
import os
import logging
import io
from http import HTTPStatus


LOCALHOST, PORT = '127.0.0.1', 8080


logging.basicConfig(
    filename='server_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)


def log_message(message: str) -> None:
    print(message)
    logging.info(message)


class PicoHTTPRequestHandler:
    '''
    Serves static files as-is. Only supports GET and HEAD.
    POST returns 403 FORBIDDEN. Other commands return 405 METHOD NOT ALLOWED.

    Supports HTTP/1.1.
    '''

    def __init__(
        self,
        request_stream: io.BufferedIOBase,
        response_stream: io.BufferedIOBase
    ):
        self.request_stream = request_stream
        self.response_stream = response_stream
        self.command = ''
        self.path = ''
        self.headers = {
            'Content-Type': 'text/html',
            'Content-Length': '0',
            'Connection': 'close'
        }
        self.data = ''
        self.handle()

    def handle(self) -> None:
        '''Handles the request.'''
        # anything but GET or HEAD will return 405
        # POST will return a 403

        # parse the request to populate
        # self.command, self.path, self.headers
        self._parse_request()

        if not self._validate_path():
            return self._return_404()

        if self.command == 'POST':
            return self._return_403()

        if self.command not in ('GET', 'HEAD'):
            return self._return_405()

        command = getattr(self, f'handle_{self.command}')
        command()

    def handle_GET(self) -> None:
        '''
        Writes headers and the file to the socket.
        '''
        self.handle_HEAD()

        with open(self.path, 'rb') as f:
            body = f.read()

        self.response_stream.write(body)
        self.response_stream.flush()  # flush to send the data

    def handle_HEAD(self) -> None:
        '''
        Writes headers to the socket.
        '''
        # default to 200 OK
        self._write_response_line(200)
        self._write_headers(
            **{
                'Content-Length': os.path.getsize(self.path)
            }
        )
        self.response_stream.flush()  # flush to send the response

    def _write_response_line(self, status_code: int) -> None:
        reponse_line = f'HTTP/1.1 {status_code} {HTTPStatus(status_code).phrase} \r\n'
        log_message(reponse_line.encode())
        self.response_stream.write(reponse_line.encode())

    def _write_headers(self, *args, **kwargs) -> None:
        headers_copy = self.headers.copy()
        headers_copy.update(**kwargs)
        header_lines = '\r\n'.join(
            f'{k}: {v}' for k, v in headers_copy.items()
        )
        log_message(header_lines.encode())
        self.response_stream.write(header_lines.encode())
        # mark the end of the headers
        self.response_stream.write(b'\r\n\r\n')

    def _parse_request(self):
        # parse the request line
        log_message('Parsing request line')
        requestline = self.request_stream.readline().decode()
        requestline = requestline.rstrip('\r\n')
        log_message(requestline)

        self.command = requestline.split(' ')[0]
        self.path = requestline.split(' ')[1]

        # parse the headers
        headers = {}
        line = self.request_stream.readline().decode()
        while line not in ('\r\n', '\n', '\r', ''):
            header = line.rstrip('\r\n').split(': ')
            headers[header[0]] = header[1]
            line = self.request_stream.readline().decode()

        log_message(headers)

    def _validate_path(self) -> bool:
        '''
        Validates the path. Returns True if the path is valid, False otherwise.
        '''
        # the path can either be a file or a directory
        # if it's a directory, look for index.html
        # if it's a file, serve it
        self.path = os.path.join(os.getcwd(), self.path.lstrip('/'))
        if os.path.isdir(self.path):
            self.path = os.path.join(self.path, 'index.html')
        elif os.path.isfile(self.path):
            pass

        if not os.path.exists(self.path):
            return False

        return True

    def _return_404(self) -> None:
        '''NOT FOUND'''
        self._write_response_line(404)
        self._write_headers()

    def _return_405(self) -> None:
        '''METHOD NOT ALLOWED'''
        self._write_response_line(405)
        self._write_headers()

    def _return_403(self) -> None:
        '''FORBIDDEN'''
        self._write_response_line(403)
        self._write_headers()


class PicoTCPServer:
    def __init__(
        self,
        socket_address: tuple[str, int],
        request_handler: PicoHTTPRequestHandler
    ) -> None:
        # Create TCP socket using IPv4 address
        self.request_handler = request_handler
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(socket_address)

        self.sock.listen()

    def serve_forever(self) -> None:
        try:
            while True:
                conn, addr = self.sock.accept()

                with conn:
                    log_message(f'Accepted connection from {addr}')
                    request_stream = conn.makefile('rb')
                    response_stream = conn.makefile('wb')
                    self.request_handler(
                        request_stream=request_stream,
                        response_stream=response_stream
                    )
                log_message(f'Closed connection from {addr}')
        except KeyboardInterrupt:
            log_message('\nFinished successfully')
        finally:
            self.sock.close()

    def __enter__(self) -> 'PicoTCPServer':
        return self

    def __exit__(self, *args) -> None:
        self.sock.close()


if __name__ == '__main__':
    log_message('Started simple TCP server')

    with PicoTCPServer((LOCALHOST, PORT), PicoHTTPRequestHandler) as server:
        log_message(f'Running on address {LOCALHOST}:{PORT}')
        server.serve_forever()
