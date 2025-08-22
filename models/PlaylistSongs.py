from peewee import *
import datetime
from models import BaseModel

class PlaylistSongs(BaseModel):
    id = PrimaryKeyField()
    playlist_id = IntegerField()
    song_id = IntegerField()
    created_by = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.datetime.now)