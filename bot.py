import discord
from discord.ext import commands
from youtubesearchpython import VideosSearch
import yt_dlp
from dotenv import load_dotenv
import os
#alberto arias

load_dotenv()
token = os.getenv("token")

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

queue = []
queue_titles = []
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}


# needed function to prevent duplicate command calls
@bot.event
async def on_message(message):
    # print(message) Just to debug
    return message


@bot.event
async def on_ready():
    print('Connected to bot: {}'.format(bot.user.name))
    print('Bot ID: {}'.format(bot.user.id))


@bot.command(pass_context=True)
async def play(ctx, *, content):
    global queue
    global queue_titles

    if isinstance(content, str) and len(content) > 0:
        if (ctx.author.voice):
            if (not ctx.voice_client):
                # If the bot is not in a voice channel, join the channel that the user is in
                channel = ctx.message.author.voice.channel
                await channel.connect()
        else:
            await ctx.send("You are not in a voice channel")

        videosSearch = VideosSearch(content, limit=1)

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
        if len(queue) == 1 and not ctx.voice_client.is_playing():
            # If there is only one song in the queue and no song is playing, play the song immediately
            ctx.voice_client.play(discord.FFmpegPCMAudio(queue[0][0], **FFMPEG_OPTIONS), after=lambda e: play_next(ctx))
            await ctx.send(f'Playing {queue[0][1]}!')
        else:
            await ctx.send(f'Added {title} to the queue!')
    elif ctx.voice_client is not None and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send('Resume playing track!')
    else:
        await ctx.send("I'm not currently playing anything. Type what you want to play!")


@bot.command(pass_context=True)
async def pause(ctx):
    if ctx.voice_client is not None and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send('Pausing current track.')
    else:
        await ctx.send("I'm not currently playing anything.")


@bot.command(pass_context=True)
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


@bot.command(pass_context=True)
async def show_queue(ctx):
    global queue
    global queue_titles
    if len(queue) == 0:
        await ctx.send('The queue is currently empty.')
    else:
        queue_list = '\n'.join([f'{i + 1}. {queue_titles[i]}' for i in range(len(queue))])
        # queue_list = '\n'.join([f'{i+1}. {queue[i]}' for i in range(len(queue))])
        await ctx.send(f'```Queue:\n{queue_list}```')


@bot.command(pass_context=True)
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


@bot.command(pass_context=True)
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
