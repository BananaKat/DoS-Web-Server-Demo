#!/usr/bin/env python3
# Sets up a simple server client arch which echos messages,
# to familiarise ourselves with how sockets communicate
# Taken from:
# https://medium.com/@sakhawy/creating-an-http-server-from-scratch-ed41ef83314b
import socket
import logging
import threading

LOCALHOST, PORT = '127.0.0.1', 8080

logging.basicConfig(
    filename='server_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)


def log_message(message: str) -> None:
    print(message)
    logging.info(message)


def server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((LOCALHOST, PORT))
        s.listen()
        print(f'Listening on {LOCALHOST}:{PORT}')
        conn, addr = s.accept()
        with conn:
            print(f'Connected to {addr}')
            while True:
                data = conn.recv(1024)
                print(f'Received {data}')
                if not data:
                    break
                conn.sendall(data)


def client(message):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((LOCALHOST, PORT))
        s.sendall(message)
        received_message = s.recv(len(message))
        print(received_message.decode())


if __name__ == '__main__':
    message = input('Input a simple message: ').encode()
    log_message('Started simple server-client arch server')

    server_thread = threading.Thread(target=server)
    client_thread = threading.Thread(target=client, args=(message,))

    server_thread.start()
    client_thread.start()

    server_thread.join()
    client_thread.join()

    log_message('Finished successfully')
