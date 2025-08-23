from peewee import *
import datetime
from .BaseModel import BaseModel
from .Users import Users

class YouTubePlaylists(BaseModel):
    id = PrimaryKeyField()
    name = TextField()
    url = TextField()
    num_plays = IntegerField(default=0)
    created_by = ForeignKeyField(Users)
    created_at = DateTimeField(default=datetime.datetime.now)