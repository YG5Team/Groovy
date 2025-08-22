from peewee import *
import datetime
from models import BaseModel

class Users(BaseModel):
    id = PrimaryKeyField()
    discord_id = CharField()
    command = CharField()
    command_usage_count = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.datetime.now)
    date_last_action = DateTimeField(default=datetime.datetime.now)