#!/usr/bin/env python3
# Uses HTTP/1.1 to host a simple HTTP server with the limitations:
# - No caching
# - No HTTPS (no encryption)
# - Only HEAD & GET requests (static files only)
# Make the server easier to DoS/DDoS by setting a semaphore to
# only be able to handle a certain amount of connections, simulating
# a server with limited resources
import socket
import os
import time
import threading

import io
from http import HTTPStatus
from server_logs import log_message


LOCALHOST, PORT = '127.0.0.1', 8080

# Fake processing time
PROCESS_TIME = 2

# ANSI colour escape codes
GREEN = '\033[32m'
BLUE = '\033[34m'
RED = '\033[31m'
YELLOW = '\033[33m'


class HTTPRequestHandler:
    # Serves static files as-is. Only supports GET and HEAD.
    # POST returns 403 FORBIDDEN. Other commands return 405 METHOD NOT ALLOWED.
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
        # Anything but GET or HEAD will return 405
        # POST will return a 403

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
        # Writes headers and the file to the socket.
        self.handle_HEAD()

        with open(self.path, 'rb') as f:
            body = f.read()

        self.response_stream.write(body)
        self.response_stream.flush()

    def handle_HEAD(self) -> None:
        # Writes headers to the socket. Default to 200 OK
        self._write_response_line(200)
        self._write_headers(
            **{
                'Content-Length': os.path.getsize(self.path)
            }
        )
        self.response_stream.flush()

    def _write_response_line(self, status_code: int) -> None:
        reponse_line = f'HTTP/1.1 {status_code} {HTTPStatus(status_code).phrase} \r\n'
        # log_message(reponse_line.encode())
        self.response_stream.write(reponse_line.encode())

    def _write_headers(self, *args, **kwargs) -> None:
        headers_copy = self.headers.copy()
        headers_copy.update(**kwargs)
        header_lines = '\r\n'.join(
            f'{k}: {v}' for k, v in headers_copy.items()
        )
        # log_message(header_lines.encode())
        self.response_stream.write(header_lines.encode())
        # Mark the end of the headers
        self.response_stream.write(b'\r\n\r\n')

    def _parse_request(self):
        # Parse the request line
        # log_message('Parsing request line')
        requestline = self.request_stream.readline().decode()
        requestline = requestline.rstrip('\r\n')
        # log_message(requestline)

        if not requestline:
            raise ValueError("Empty requestline received")

        components = requestline.split(' ')
        if len(components) < 3:
            raise ValueError("Invalid HTTP request line")
        self.command, self.path, *_ = components

        # Parse the headers
        headers = {}
        line = self.request_stream.readline().decode()
        while line not in ('\r\n', '\n', '\r', ''):
            header = line.rstrip('\r\n').split(': ')
            headers[header[0]] = header[1]
            line = self.request_stream.readline().decode()

        # log_message(headers)

    def _validate_path(self) -> bool:
        self.path = os.path.join(os.getcwd(), self.path.lstrip('/'))
        if os.path.isdir(self.path):
            self.path = os.path.join(self.path, 'index.html')
        elif os.path.isfile(self.path):
            pass

        if not os.path.exists(self.path):
            return False

        return True

    def _return_403(self) -> None:
        # Error 403: FORBIDDEN
        self._write_response_line(403)
        self._write_headers()

    def _return_404(self) -> None:
        # Error 404: NOT FOUND
        self._write_response_line(404)
        self._write_headers()

    def _return_405(self) -> None:
        # Error 405: METHOD NOT ALLOWED
        self._write_response_line(405)
        self._write_headers()


class TCPServer:
    def __init__(
        self,
        socket_address: tuple[str, int],
        request_handler: HTTPRequestHandler,
        max_connections: int
    ) -> None:
        # Create TCP socket using IPv4 address
        # Use a semaphore to manage the concurrent connections
        self.request_handler = request_handler
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(socket_address)
        self.sock.listen()
        self.semaphore = threading.Semaphore(max_connections)

        self.connection_count = 0
        self.connection_count_lock = threading.Lock()

    def serve_forever(self) -> None:
        try:
            while True:
                conn, addr = self.sock.accept()

                if not self.semaphore.acquire(blocking=False):
                    log_message(
                        f'Too many connections: {addr} rejected',
                        YELLOW
                    )
                    conn.close()
                    continue

                # Handle the connection in a separate thread
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(conn, addr)
                )
                client_thread.daemon = True
                client_thread.start()

        except KeyboardInterrupt:
            log_message('Finished successfully', GREEN)
        finally:
            self.sock.close()

    def handle_client(self, conn, addr):
        try:
            with conn:
                log_message(f'Accepted connection from {addr}', GREEN)
                self.update_connection_count(increment=True)

                request_stream = conn.makefile('rb')
                response_stream = conn.makefile('wb')
                # Handle request
                self.request_handler(
                    request_stream=request_stream,
                    response_stream=response_stream
                )
                # Simulate heavy process
                time.sleep(PROCESS_TIME)
        except BrokenPipeError:
            log_message(
                f'Connection error from {addr}: Broken pipe (client disconnected)',
                RED
            )
        except Exception as error:
            log_message(f'Connection error from {addr}: {error}', RED)
        finally:
            self.semaphore.release()
            log_message(f'Closed connection from {addr}', BLUE)
            self.update_connection_count(increment=False)

    def update_connection_count(self, increment: bool) -> None:
        with self.connection_count_lock:
            self.connection_count += 1 if increment else -1
            log_message(f'Connection count: {self.connection_count}')

    def __enter__(self) -> 'TCPServer':
        return self

    def __exit__(self, *args) -> None:
        self.sock.close()


def get_max_connections() -> int:
    try:
        max_conns = int(input('Enter the maximum number of connections: '))
    except KeyboardInterrupt:
        exit('\nCancelled server run')
    except ValueError:
        exit("Invalid input: Max connections must be an integer")

    return max_conns


def run_tcp_server(max_conns: int) -> None:
    try:
        with TCPServer((LOCALHOST, PORT), HTTPRequestHandler, max_conns) as server:
            log_message(f'TCP Server listening on address {LOCALHOST}:{PORT}')
            server.serve_forever()
    except OSError as error:
        if error.errno == 98:
            log_message(
                f'Error: Address {LOCALHOST}:{PORT} is already in use', RED)
        else:
            log_message(f'An error occurred: {error}', RED)


if __name__ == '__main__':
    max_conns = get_max_connections()

    log_message('Started simple TCP server')
    run_tcp_server(max_conns)
