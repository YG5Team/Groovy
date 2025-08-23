from peewee import *
from helpers import *
from .BaseModel import BaseModel
from .Songs import Songs
from .Users import Users

class SongQueue(BaseModel):
    id = PrimaryKeyField()
    position = IntegerField()
    server_id = CharField()
    song_id = ForeignKeyField(Songs)
    created_by = ForeignKeyField(Users)

    def append(self,song: Songs | None = None):
        if song is None:
            raise RuntimeError('A Valid Song must be provided.')
        print(song)
        entry = self.get(song_id = song.id)
        print(entry)
        die()
        return song
