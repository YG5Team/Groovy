from datetime import datetime

import discord

from models import *
from helpers import *

FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

def establish_globals(author):
    user, created = Users.get_or_create(discord_id=author.id, name=author.name, global_name=author.global_name)
    GlobalSettings.CURRENT_USER = user
    GlobalSettings.CURRENT_SERVER = author.guild.id
    return user

def get_discord_tag( discord_id = None ):
    if isinstance(discord_id, int):
        return "<@" + str(discord_id) + ">"
    return"<@" + str(GlobalSettings.CURRENT_USER.discord_id) + ">"

async def play_next(ctx):
    SongQueue.pop()
    if SongQueue.queue_length() > 0:
        # if there are songs in the queue, play the next one
        next_song = SongQueue.get_first_song()
        if next_song is not None:
            song = Songs.get_by_id(next_song.song)
            GlobalSettings.CURRENT_SONG = song
            url = await song.get_url()
            source = discord.FFmpegOpusAudio(url, **FFMPEG_OPTIONS)
            ctx.voice_client.play(source, after=_after_factory(ctx))
    else:
        await ctx.voice_client.disconnect()
        await ctx.send('Disconnected from the voice channel.')


def _after_factory(ctx):
    def _after_playing(error):
        # hop back to the bot loop safely
        try:
            asyncio.run_coroutine_threadsafe(play_next(ctx), ctx.bot.loop)
        except Exception:
            pass
    return _after_playing

async def play_queue(ctx):
    first_song = SongQueue.get_first_song()
    if first_song is not None:
        song = Songs.get_by_id(first_song.song)
        GlobalSettings.CURRENT_SONG = song
        url = await song.get_url()
        source = discord.FFmpegOpusAudio(url, **FFMPEG_OPTIONS)
        ctx.voice_client.play(source, after=_after_factory(ctx))
        await ctx.send(f'Playing {song.title} from Queue! 🎶')

async def add_to_song_queue(ctx, song_id: int):
    song, play_now = SongQueue.add_to_queue(song_id)

    if SongQueue.queue_length() == 1 and not ctx.voice_client.is_playing():
        GlobalSettings.CURRENT_SONG = song
        url = await song.get_url_(True)  # ASYNC
        source = discord.FFmpegOpusAudio(url, **FFMPEG_OPTIONS)
        ctx.voice_client.play(source, after=_after_factory(ctx))
        await ctx.send(f'Playing {song.title}! 🎶')
    else:
        await ctx.send(f'Added {song.title} to the queue! 🎶')

async def add_youtube_playlist_to_queue(ctx, yt_playlist):

    yt_playlist.updated_at = datetime.now()
    yt_playlist.num_plays += 1
    yt_playlist.save()

    songs = yt_playlist.get_songs()

    for song in songs:

        SongQueue.add_to_queue(song.id)
