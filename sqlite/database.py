from peewee import *

import models

# Connect or create DB file
sqlite_db = SqliteDatabase('./sqlite/groovy.sqlite', pragmas={
    'journal_mode': 'wal',  # WAL-mode.
    'cache_size': -64 * 1000,  # 64MB cache.
    'foreign_keys': 1,
    'ignore_check_constraints': 0,
    'synchronous': 0})  # Let the OS manage syncing.

def check_db_connection():
    sqlite_db.connect()

def create_db():
    check_db_connection()

    try:
        sqlite_db.create_tables(models.creation_order)
        print("Tables created.")
    except Exception as e:
        raise DataError("Error creating tables:", e)

    sqlite_db.commit()
    sqlite_db.close()