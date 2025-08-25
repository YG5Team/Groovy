import yt_dlp
from peewee import *
import datetime
from helpers import *
from .BaseModel import BaseModel
from .Users import Users
from .Songs import Songs

class YouTubePlaylists(BaseModel):
    id = PrimaryKeyField()
    title = TextField()
    search_id = CharField(unique=True)
    url = TextField()
    num_plays = IntegerField(default=0)
    expected_num_items = IntegerField(default=0)
    created_by = ForeignKeyField(Users)
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)

    def get_decoded_url(self):
        return base64_decode(self.url)

    @classmethod
    def validate_url(cls, url):
        url_template = "https://www.youtube.com/playlist?list="
        if not url:
            return False, "Please provide a playlist URL: ".format(url_template)

        if url_template not in url:
            return False, url + " is not a valid youtube playlist URL."

        return True, url

    def get_songs_query(self):
        return Songs.select().join(YouTubePlaylistSongs).where(YouTubePlaylistSongs.youtube_playlist == self.id)

    def get_songs(self):
        return self.get_songs_query().execute()

    def song_count(self):
        return self.get_songs_query().count()

    @classmethod
    def search(cls, content):
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

    @classmethod
    def save_youtube_playlist(cls, content):

        results = cls.search(content)

        if isinstance(results, str):
            return results, None, False

        url = base64_encode(content)
        entries = results['entries']

        yt_playlist, created = cls.get_or_create(search_id=results['id'], defaults={
            'title': results['title'],
            'created_by': GlobalSettings.CURRENT_USER.id,
            'url': url,
            'expected_num_items': len(entries),
        })

        if not created:
            yt_playlist.url = url
            yt_playlist.updated_at = datetime.datetime.now()
            yt_playlist.save()

        num_new_songs = 0
        for video in entries:
            if not video:
                print("ERROR: Unable to get info. Continuing...")
                continue

            info = {
                "title": video['title'],
                'uploader': video['uploader'],
                "url": video['url'],
                "playlist": yt_playlist.title
            }

            song, song_created = Songs.save_song(info["title"])
            if song_created:
                num_new_songs += 1

            link, link_created = YouTubePlaylistSongs.get_or_create(
                song=song.id,
                youtube_playlist=yt_playlist.id,
                defaults={
                    'created_by': GlobalSettings.CURRENT_USER.id
                })

        return num_new_songs, yt_playlist, created

class YouTubePlaylistSongs(BaseModel):
    id = PrimaryKeyField()
    youtube_playlist = ForeignKeyField(YouTubePlaylists, backref='youtube_playlist_songs')
    song = ForeignKeyField(Songs, backref='youtube_playlist_songs')
    created_by = ForeignKeyField(Users)
    created_at = DateTimeField(default=datetime.datetime.now)