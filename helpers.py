import asyncio
import inspect
import os
import sys
import base64
import traceback

from dotenv import load_dotenv

class GlobalSettings:
    CURRENT_USER :object = None
    CURRENT_SONG : object = None
    CURRENT_SERVER : int | None = None
    LAST_ERROR = None

    def __init__(self):
        self.CURRENT_USER = None
        self.CURRENT_SONG = None
        self.CURRENT_SERVER = None
        self.LAST_ERROR = None

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
            caller = inspect.getframeinfo(inspect.stack()[1][0])
            current_filename = caller.filename
            current_line = caller.lineno
            output = f"Filename: {current_filename}, Line number: {current_line}: {content}"
            print(output, file=file)
            print('\n', file=file)
            print(output)

def format_error(error):
    return "".join(traceback.format_exception(type(error), error, error.__traceback__))

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
