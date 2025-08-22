from peewee import *
import datetime
from models import BaseModel

class YouTubePlaylists(BaseModel):
    id = PrimaryKeyField()
    name = TextField()
    url = TextField()
    num_plays = IntegerField(default=0)
    created_by = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.datetime.now)