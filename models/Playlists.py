from peewee import *
import datetime
from .BaseModel import BaseModel
from .Users import Users
from .Songs import Songs

class Playlists(BaseModel):
    id = PrimaryKeyField()
    server_id = CharField()
    name = TextField()
    plays_counter = IntegerField(default=0)
    created_by = ForeignKeyField(Users)
    created_at = DateTimeField(default=datetime.datetime.now)


class PlaylistSongs(BaseModel):
    id = PrimaryKeyField()
    playlist = ForeignKeyField(Playlists, backref='playlist_songs')
    song = ForeignKeyField(Songs, backref='playlist_songs')
    created_by = ForeignKeyField(Users)
    created_at = DateTimeField(default=datetime.datetime.now)