import asyncio
import os
import sys
import base64

from dotenv import load_dotenv

class GlobalSettings:
    CURRENT_USER :object = None
    CURRENT_SONG : object = None
    CURRENT_SERVER : int | None = None

    def __init__(self):
        self.CURRENT_USER = None
        self.CURRENT_SONG = None
        self.CURRENT_SERVER = None

load_dotenv()
DEBUG = os.getenv("DEBUG") != '0'
debug_file_name = 'debug.log'
error_file_name = 'error.log'

"""
For debugging purposes ONLY kills app
"""
def die():
    if DEBUG:
        asyncio.get_event_loop().stop()
        sys.exit(0)

def dd(content, message = 1):
    if DEBUG:
        with open(debug_file_name, "w") as file:
            if isinstance(message, str):
                file.write(str(message) + "\n")
            print(content, file=file)
            print(content)
        asyncio.get_event_loop().stop()
        sys.exit(message)

def debug(content, truncate = False):
    if DEBUG:
        if truncate:
            f = open(debug_file_name, 'r+')
            f.truncate(0)
        with open(debug_file_name, "a") as file:
            print(content, file=file)
            print('\n', file=file)
            print(content)

def log_error(content):
    with open(error_file_name, "a") as file:
        print(content, file=file)
        print('\n', file=file)
        print(content)

def init_logs():
    open(debug_file_name, 'w')
    open(error_file_name, 'w')
    print('LOG FILES HAVE BEEN TRUNCATED')


def base64_encode(string):
    string_bytes = string.encode("ascii")
    return base64.b64encode(string_bytes)

def base64_decode(string):
    string_bytes = base64.b64decode(string)
    return string_bytes.decode("ascii")
