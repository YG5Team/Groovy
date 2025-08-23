from peewee import *
import datetime
from .BaseModel import BaseModel
from .Users import Users

class CommandCount(BaseModel):
    id = PrimaryKeyField()
    user_id = ForeignKeyField(Users)
    command = CharField()
    counter = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.datetime.now)
    date_last_action = DateTimeField(default=datetime.datetime.now)