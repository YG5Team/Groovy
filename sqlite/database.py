import logging
import os
import sys
import importlib, inspect
from peewee import *
import sqlite3

logger = logging.getLogger('peewee')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)


sqlite_db = SqliteDatabase('groovy.db', pragmas={
    'journal_mode': 'wal',  # WAL-mode.
    'cache_size': -64 * 1000,  # 64MB cache.
    'synchronous': 0})  # Let the OS manage syncing.

def create_db():
    #@TODO: get all models and place in
    #Connect or create DB file
    conn = sqlite3.connect('./sqlite/groovy.db')
    conn.close()

    files = [os.path.join(dirpath, f) for (dirpath, dirnames, filenames) in os.walk('./models') for f in filenames]
    tables = [];
    for filename in files:
        if '__pycache__' in filename:
            continue
        filename = filename.replace('.' + os.sep, '').replace(os.sep, '.').replace('.py', '')
        for name, cls in inspect.getmembers(importlib.import_module(filename), inspect.isclass):
            if cls.__module__ == filename:
                tables.append(cls)
                # print([name, cls])

    sqlite_db.connect()
    sqlite_db.create_tables(tables)
    sys.exit()

class BaseModel(Model):
    class Meta:
        database = sqlite_db
