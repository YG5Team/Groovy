from peewee import *
import datetime
from .BaseModel import BaseModel

class Users(BaseModel):
    id = PrimaryKeyField()
    discord_id = IntegerField(unique=True)
    name = CharField()
    global_name = CharField()
    created_at = DateTimeField(default=datetime.datetime.now)
    date_last_action = DateTimeField(default=datetime.datetime.now)