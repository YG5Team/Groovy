from sqlite.database import *
from peewee import *

class SongQueue(BaseModel):
    id = PrimaryKeyField()
    position = IntegerField()
    server_id = CharField()
    song_id = IntegerField(default=0)
    playlist_id = IntegerField(default=0)
    created_by = IntegerField(default=0)
