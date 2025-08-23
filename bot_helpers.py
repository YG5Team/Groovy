import discord
import yt_dlp
from youtubesearchpython import VideosSearch

from models import *
from helpers import *

ACTIVE_USER = None
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

def establish_user(author):
    global ACTIVE_USER
    user, created = Users.get_or_create(discord_id=author.id, name=author.name, global_name=author.global_name)
    ACTIVE_USER = user
    return user

def search_song(content):
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

    results = yt_dlp.YoutubeDL(ydl_opts).extract_info(link, download=False)

    url = base64_encode(results['url'])

    song, created = Songs.get_or_create(title=results['title'], url=url, search_id=results['id'], defaults={'created_by': ACTIVE_USER.id})

    return song

async def add_to_song_queue(ctx, song):

    SongQueue.append(song)

    if len(songQueue) == 1 and not ctx.voice_client.is_playing():
        song = songQueue[0]
        # If there is only one song in the queue and no song is playing, play the song immediately
        ctx.voice_client.play(discord.FFmpegPCMAudio(song.url, **FFMPEG_OPTIONS), after=lambda e: play_next(ctx))
        await ctx.send(f'Playing {song.title}! 🎶')
    else:
        await ctx.send(f'Added {song.title} to the queue! 🎶')

def play_next(ctx):
    global songQueue
    songQueue.pop(0)
    if len(songQueue) > 0:
        # if there are songs in the queue, play the next one
        song = songQueue[0]
        ctx.voice_client.play(discord.FFmpegPCMAudio(song.url, **FFMPEG_OPTIONS), after=lambda e: play_next(ctx))
    else:
        ctx.voice_client.disconnect()
        ctx.send('Disconnected from the voice channel.')