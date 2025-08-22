from sqlite.database import *
from peewee import *
import datetime

class Playlists(BaseModel):
    id = PrimaryKeyField()
    server_id = CharField()
    name = TextField()
    num_plays = IntegerField(default=0)
    created_by = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.datetime.now)