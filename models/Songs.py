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

        # If stale, refresh by calling async search
        if (now - self.updated_at) > datetime.timedelta(hours=2):
            print('Refreshing Download URL for song: ' + str(self.id))
            results = await Songs.search_async(self.title)  # <- async

            url = base64_encode(results['url'])

            if increase_counter:
                self.plays_counter += 1

            self.title = results['title']
            self.url = url
            self.updated_at = datetime.datetime.now()
            self.save()

            return results['url']

        elif increase_counter:
            self.plays_counter += 1
            self.save()

        return self.get_decoded_url()

    @classmethod
    async def search_async(cls, content: str):
        """Async wrapper that offloads VideosSearch + yt_dlp to a thread."""
        def _blocking_search():
            # VideosSearch is blocking
            video_search = VideosSearch(content, limit=1).result()
            link = None

            # your existing fallback logic
            if 'result' in video_search and video_search['result']:
                first = video_search['result'][0]
                link = first.get('link') or first.get('url')

            if not link:
                raise AttributeError("No link found in search result")

            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
                'nocheckcertificate': True,
                'noplaylist': True,
                'prefer_ffmpeg': True,
                # NOTE: you were postprocessing to MP3; for streaming to Discord
                # we generally don't need to transcode here. Keep download=False.
                # If you truly need MP3 URLs, keep postprocessors, but it’s slower.
                # 'postprocessors': [...]
            }
            if DEBUG:
                ydl_opts['cachedir'] = False

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=False)
            return info

        return await asyncio.to_thread(_blocking_search)

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

    """
    @FIXME: we need to think of a better way as of now we always have to ping the search
            and create the video download.
            Saving the generated URL is pointless. IDK what we should do here.
    """
    @classmethod
    def save_song(cls, content):
        """Async version of save_song that uses search_async."""
        results = await cls.search_async(content)
        url = base64_encode(results['url'])

        song, created = cls.get_or_create(
            search_id=results['id'],
            defaults={
                'title': results['title'],
                'created_by': GlobalSettings.CURRENT_USER.id,
                'url': url,
            }
        )

        # we have to update the URL as the saved one could be expired
        if not created:
            song.title = results['title']
            song.url = url
            song.updated_at = datetime.datetime.now()
            song.save()

        return song, created
