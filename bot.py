import discord
from discord.ext import commands
from youtubesearchpython import VideosSearch
import yt_dlp
from dotenv import load_dotenv
import os

load_dotenv()
token = os.getenv("token")

# intents = discord.Intents.all()
bot = discord.Bot(command_prefix='!', intents=discord.Intents.all())

queue = []
queue_titles = []
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
guild_ids = ['759520511553830913', '729233019034009680', '698704305636769844']


# https://www.youtube.com/watch?v=I1wHDY4DGRI
# https://www.youtube.com/watch?v=I1wHDY4DGRI&ab_channel=s%C3%A4%C3%A4st%C3%B6possupaisti

@bot.slash_command(name="play",
                   guild_ids=guild_ids)  # Add the guild ids in which the slash command will appear. If it should be in all, remove the argument, but note that it will take some time (up to an hour) to register the command if it's for all guilds.
async def play(ctx, search=None):
    global queue
    global queue_titles

    if isinstance(search, str):
        voice_channel = ctx.author.voice.channel
        voice_client = ctx.voice_client
        if ctx.voice_client is None:
            voice_client = await voice_channel.connect()
        else:
            await ctx.voice_client.move_to(voice_channel)

        videosSearch = VideosSearch(search, limit=1)

        link = videosSearch.result()['result'][0]['link']

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

        url = yt_dlp.YoutubeDL(ydl_opts).extract_info(link, download=False)['url']
        title = yt_dlp.YoutubeDL(ydl_opts).extract_info(link, download=False)['title']

        queue.append((url, title))
        queue_titles.append(title)
        if len(queue) == 1 and not voice_client.is_playing():
            # If there is only one song in the queue and no song is playing, play the song immediately
            voice_client.play(discord.FFmpegPCMAudio(queue[0][0], **FFMPEG_OPTIONS), after=lambda e: play_next(ctx))
            await ctx.send(f'Playing {queue[0][1]}!')
        else:
            await ctx.send(f'Added {title} to the queue!')
    elif ctx.voice_client is not None and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send('Resume playing track!')
    else:
        await ctx.send("I'm not currently playing anything. Type what you want to play!")


@bot.slash_command(name="pause", guild_ids=guild_ids)
async def pause(ctx):
    if ctx.voice_client is not None and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send('Pausing current track.')
    else:
        await ctx.send("I'm not currently playing anything.")


@bot.slash_command(name="resume", guild_ids=guild_ids)
async def resume(ctx):
    if ctx.voice_client is not None and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send('Resume playing track!')
    else:
        await ctx.send("I'm not currently playing anything.")


def play_next(ctx):
    global queue
    global queue_titles
    if len(queue) > 0:
        # if there are songs in the queue, play the next one
        queue.pop(0)
        queue_titles.pop(0)
        if len(queue) > 0:
            ctx.voice_client.play(discord.FFmpegPCMAudio(queue[0][0], **FFMPEG_OPTIONS), after=lambda e: play_next(ctx))
            ctx.send(f'Skipping to the next song in the queue.')
        else:
            ctx.send('No more songs in the queue.')
    else:
        ctx.voice_client.disconnect()
        ctx.send('Disconnected from the voice channel.')


@bot.slash_command(name="queue", guild_ids=guild_ids)
async def show_queue(ctx):
    global queue
    global queue_titles
    if len(queue) == 0:
        await ctx.send('The queue is currently empty.')
    else:
        queue_list = '\n'.join([f'{i + 1}. {queue_titles[i]}' for i in range(len(queue))])
        # queue_list = '\n'.join([f'{i+1}. {queue[i]}' for i in range(len(queue))])
        await ctx.send(f'```Queue:\n{queue_list}```')


@bot.slash_command(name="skip", guild_ids=guild_ids)
async def skip(ctx):
    global queue
    global queue_titles
    if ctx.voice_client is not None and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        if len(queue) > 0:
            # if there are songs in the queue, play the next one
            next_song = queue.pop(0)
            queue_titles.pop(0)
            ctx.voice_client.play(discord.FFmpegPCMAudio(next_song, **FFMPEG_OPTIONS))
            await ctx.send('Skipping to the next song in the queue.')
        else:
            await ctx.send('No more songs in the queue.')
    else:
        await ctx.send("I'm not currently playing anything.")


@bot.slash_command(name="stop", guild_ids=guild_ids)
async def stop(ctx):
    global queue
    global queue_titles
    queue = []
    queue_titles = []
    if ctx.voice_client is not None:
        await ctx.voice_client.disconnect()
        await ctx.send('Disconnected from the voice channel.')
    else:
        await ctx.send("I'm not currently connected to a voice channel.")


bot.run(token)
