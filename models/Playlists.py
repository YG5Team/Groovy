from peewee import *
import datetime
from .BaseModel import BaseModel
from .Users import Users

class Playlists(BaseModel):
    id = PrimaryKeyField()
    server_id = CharField()
    name = TextField()
    plays_counter = IntegerField(default=0)
    created_by = ForeignKeyField(Users, backref='playlists')
    created_at = DateTimeField(default=datetime.datetime.now)