from .BaseModel import BaseModel
from .CommandCount import CommandCount
from .Playlists import Playlists
from .PlaylistSongs import PlaylistSongs
from .SongQueue import SongQueue
from .Songs import Songs
from .Users import Users
from .YouTubePlaylists import YouTubePlaylists
from .YouTubePlaylistSongs import YouTubePlaylistSongs

__all__ = [
    'BaseModel',
    'Playlists',
    'PlaylistSongs',
    'SongQueue',
    'Songs',
    'Users',
    'YouTubePlaylists',
    'YouTubePlaylistSongs',
]

creation_order = [
    Users,
    CommandCount,
    Songs,
    SongQueue,
    Playlists,
    PlaylistSongs,
    YouTubePlaylists,
    YouTubePlaylistSongs
]