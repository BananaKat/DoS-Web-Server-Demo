#!/usr/bin/env python3
# Code to write server logs to a file.
# Written by Jason Phua (z5592964)
import os
import logging


LOG_FILE = 'server_log.txt'
RESET = '\033[0m'


# If log file does not exist, create it
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'w') as f:
        pass

logging.basicConfig(
    filename='server_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)


def log_message(message: str, colour: str = RESET) -> None:
    print(f'{colour}{message}{RESET}')
    logging.info(message)


if __name__ == '__main__':
    log_message('Testing message logger')
