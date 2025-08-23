from peewee import *
import datetime
from .BaseModel import BaseModel
from .Users import Users

class Songs(BaseModel):
    id = PrimaryKeyField()
    title = TextField()
    search_id = CharField(unique=True)
    url = TextField()
    plays_counter = IntegerField(default=0)
    created_by = ForeignKeyField(Users, backref='songs')
    created_at = DateTimeField(default=datetime.datetime.now)