import logging
import os
import importlib, inspect
from peewee import *

import models
from models import *

logger = logging.getLogger('peewee')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

# Connect or create DB file
sqlite_db = SqliteDatabase('./sqlite/groovy.sqlite', pragmas={
    'journal_mode': 'wal',  # WAL-mode.
    'cache_size': -64 * 1000,  # 64MB cache.
    'foreign_keys': 1,
    'ignore_check_constraints': 0,
    'synchronous': 0})  # Let the OS manage syncing.

def create_db():
    #Import model files dynamically
    # files = [os.path.join(dirpath, f) for (dirpath, dirnames, filenames) in os.walk('./models') for f in filenames]
    # tables = []
    # #Loop through files
    # for filename in files:
    #     if '__pycache__' in filename:
    #         continue
    #     filename = filename.replace('.' + os.sep, '').replace(os.sep, '.').replace('.py', '')
    #     for name, cls in inspect.getmembers(importlib.import_module(filename), inspect.isclass):
    #         if cls.__module__ == filename and issubclass(cls, BaseModel) and cls != BaseModel:
    #             tables.append(cls)
    #             # print([name, cls])

    sqlite_db.connect()

    try:
        sqlite_db.create_tables(models.creation_order)
        print("Tables created.")
    except Exception as e:
        raise DataError("Error creating tables:", e)

    sqlite_db.commit()
    sqlite_db.close()