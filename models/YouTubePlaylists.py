import yt_dlp
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

    @classmethod
    def search(cls, content):
        content = 'https://www.youtube.com/playlist?list=PLDIoUOhQQPlWt8OpaGG43OjNYuJ2q9jEN'

        url_template = "https://www.youtube.com/playlist?list="
        if not content:
            return "Please provide a playlist URL: ".format(url_template)

        if url_template not in content:
            return content + " is not a valid youtube playlist URL."

        ydl_opts = {
            'nocheckcertificate': True,
            "ignoreerrors": True,
            "quiet": True,
            "simulate": True,
            "allow_playlist_files": False,
            'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
            'extract_flat': True
        }

        return yt_dlp.YoutubeDL(ydl_opts).extract_info(content, download=False)