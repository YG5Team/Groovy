from peewee import *
import datetime
from .BaseModel import BaseModel
from .Playlists import Playlists
from .Songs import Songs
from .Users import Users

class PlaylistSongs(BaseModel):
    id = PrimaryKeyField()
    playlist_id = ForeignKeyField(Playlists, backref='playlist_songs')
    song_id = ForeignKeyField(Songs, backref='playlist_songs')
    created_by = ForeignKeyField(Users, backref='playlist_songs')
    created_at = DateTimeField(default=datetime.datetime.now)