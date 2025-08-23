from peewee import *

db = SqliteDatabase('./sqlite/groovy.sqlite', pragmas={
            'journal_mode': 'wal',  # WAL-mode.
            'cache_size': -64 * 1000,  # 64MB cache.
            'foreign_keys': 1,
            'ignore_check_constraints': 0,
            'synchronous': 0})  # Let the OS manage syncing.

class BaseModel(Model):
    class Meta:
        database = db