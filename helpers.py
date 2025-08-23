import os
import sys
import base64

from dotenv import load_dotenv

load_dotenv()
DEBUG = os.getenv("DEBUG")

"""
For debugging purposes ONLY kills app
"""

def die():
    if DEBUG:
        sys.exit(0)

def dd(content, message = 1):
    if DEBUG:
        debug_file_name = 'debug.txt'
        f = open(debug_file_name, 'r+')
        f.truncate(0)
        with open(debug_file_name, "a") as file:
            if isinstance(message, str):
                file.write(str(message) + "\n")
            print(content, file=file)
        sys.exit(message)

def debug(content, truncate = False):
    if DEBUG:
        debug_file_name = 'debug.txt'
        if truncate:
            f = open(debug_file_name, 'r+')
            f.truncate(0)
        with open(debug_file_name, "a") as file:
            print(content, file=file)

def base64_encode(string):
    string_bytes = string.encode("ascii")
    return base64.b64encode(string_bytes)

def base64_decode(string):
    string_bytes = base64.b64decode(string)
    return string_bytes.decode("ascii")
