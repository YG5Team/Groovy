from peewee import *
import datetime
import yt_dlp
from youtubesearchpython import VideosSearch
from helpers import *
from .BaseModel import BaseModel
from .Users import Users

class Songs(BaseModel):
    id = PrimaryKeyField()
    title = TextField()
    search_id = CharField(unique=True)
    url = TextField()
    plays_counter = IntegerField(default=0)
    created_by = ForeignKeyField(Users)
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)
    last_played_on = DateTimeField(default=datetime.datetime.now)

    def get_decoded_url(self):
        return base64_decode(self.url)

    def get_url(self):
        now = datetime.datetime.now()
        if (now - self.updated_at) > datetime.timedelta(hours=2):
            print('Refreshing Download URL for song: ' + str(self.id))
            results = Songs.search(self.title)

            url = base64_encode(results['url'])
            self.title = results['title']
            self.url = url
            self.updated_at = datetime.datetime.now()
            self.save()

            return results['url']

        return self.get_decoded_url()

    @classmethod
    def search(cls, content):
        video_search = VideosSearch(content, limit=1).result()
        link = video_search['result'][0]['link']
        if not link:
            first_result = video_search.result()['result'][0]
            if 'link' in first_result:
                link = first_result['link']
            elif 'url' in first_result:
                link = first_result['url']
            else:
                raise AttributeError(first_result)

        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
            'nocheckcertificate': True,
            'noplaylist': True,
            'prefer_ffmpeg': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192'
            }]
        }

        if DEBUG:
            ydl_opts['cachedir'] = False

        return yt_dlp.YoutubeDL(ydl_opts).extract_info(link, download=False)