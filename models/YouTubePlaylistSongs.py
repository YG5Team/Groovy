from peewee import *
import datetime
from .BaseModel import BaseModel
from .Users import Users
from .Songs import Songs
from .YouTubePlaylists import YouTubePlaylists

class YouTubePlaylistSongs(BaseModel):
    id = PrimaryKeyField()
    youtube_playlist_id = ForeignKeyField(YouTubePlaylists, backref='youtube_playlist_songs')
    song_id = ForeignKeyField(Songs, backref='youtube_playlist_songs')
    created_by = ForeignKeyField(Users, backref='youtube_playlist_songs')
    created_at = DateTimeField(default=datetime.datetime.now)