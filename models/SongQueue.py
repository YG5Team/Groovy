from peewee import *
from helpers import *
from .BaseModel import BaseModel
from .Songs import Songs
from .Users import Users

class SongQueue(BaseModel):
    id = PrimaryKeyField()
    position = IntegerField()
    server_id = CharField()
    song = ForeignKeyField(Songs, backref='queue')
    created_by = ForeignKeyField(Users)

    @classmethod
    def queue_length(cls):
        return cls.select().where(cls.server_id == GlobalSettings.CURRENT_SERVER).count()

    @classmethod
    def pop(cls):
        last_song = cls.get_last_song()
        if last_song is None:
            return
        print([
            GlobalSettings.CURRENT_SONG.id,
            last_song.song
        ])
        if GlobalSettings.CURRENT_SONG.id == last_song.song:
            return cls.delete().where(cls.id == last_song.id).execute()
        else:
            raise RuntimeError('Current song id ' + str(GlobalSettings.CURRENT_SONG.id) + ' does not match next in queue ID: ' + str(last_song.id) + '!!!')

    @classmethod
    def clear(cls):
        return cls.delete().where(cls.server_id == GlobalSettings.CURRENT_SERVER).execute()

    @classmethod
    def add_to_queue(cls, song_id: int):
        song = Songs.get_by_id(song_id)
        position = 1
        current_queue = cls.get_last_song()

        if current_queue is not None:
            position = current_queue.position + 1

        record, play_now = cls.get_or_create(song=song_id, defaults={
            'position': position,
            'server_id': GlobalSettings.CURRENT_SERVER,
            'created_by': GlobalSettings.CURRENT_USER.id,
        })

        return song, play_now

    @classmethod
    def get_last_song(cls):
        return cls.select(cls, Songs).join(Songs).where(cls.server_id == GlobalSettings.CURRENT_SERVER).order_by(-cls.position).get_or_none()

    @classmethod
    def get_first_song(cls):
        return cls.select(cls, Songs).join(Songs).where(cls.server_id == GlobalSettings.CURRENT_SERVER).order_by(+cls.position).get_or_none()

    @classmethod
    def remove_from_queue(cls, song: int):
        die()

    @classmethod
    def get_queue(cls):
        return cls.select().where(cls.server_id == GlobalSettings.CURRENT_SERVER).order_by(+cls.position).dicts()

    @classmethod
    def songs_in_queue(cls):
        result = {}
        queue = cls.get_queue()
        for song in queue:
            result[song['position']] = Songs.get_by_id(song['song']).title
        return result
