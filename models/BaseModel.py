from peewee import Model, SqliteDatabase

class BaseModel(Model):
    class Meta:
        database =  SqliteDatabase('groovy.sqlite', pragmas={
            'journal_mode': 'wal',  # WAL-mode.
            'cache_size': -64 * 1000,  # 64MB cache.
            'foreign_keys': 1,
            'ignore_check_constraints': 0,
            'synchronous': 0})  # Let the OS manage syncing.