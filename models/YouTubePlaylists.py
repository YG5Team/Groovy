import yt_dlp
from peewee import *
import datetime
from helpers import *
from .BaseModel import BaseModel
from .Users import Users

class YouTubePlaylists(BaseModel):
    id = PrimaryKeyField()
    title = TextField()
    search_id = CharField(unique=True)
    url = TextField()
    num_plays = IntegerField(default=0)
    created_by = ForeignKeyField(Users)
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)

    def get_decoded_url(self):
        return base64_decode(self.url)

    @classmethod
    def search(cls, content):
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

        if DEBUG:
            ydl_opts['cachedir'] = False

        return yt_dlp.YoutubeDL(ydl_opts).extract_info(content, download=False)