from sqlite.database import *

class BaseModel(Model):
    class Meta:
        database = sqlite_db