import traceback
import discord
from discord.ext import commands
from youtubesearchpython import VideosSearch
import yt_dlp 
from dotenv import load_dotenv
import os
import requests
import xml.etree.ElementTree as ET
import sys
from Song import Song
import mysql.connector

# @TODO: FIX PYTHON PACKAGES SPECIFICALLY DISCORD.PY
# EITHER USE MAIN BRANCH OF REPO OR WAIT FOR UPDATE OF PACKAGE (MAY NEED TO UPDATE OTHER PACKAGES) https://github.com/Rapptz/discord.py
# @ISSUE: https://github.com/Rapptz/discord.py/issues/10207

load_dotenv()

if os.getenv('DEBUG'):
    token = os.environ['DEBUG_TOKEN']
else:
    token = os.environ['TOKEN']

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

# get args
if len(sys.argv) == 2:
    if sys.argv[1] == "debug":
        token = os.environ['DEBUG_TOKEN']
        bot = commands.Bot(command_prefix='@', intents=discord.Intents.all())

songQueue = []
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

@bot.event
async def on_ready():
    global songQueue
    print('Connected to bot: {}'.format(bot.user.name))
    print('Bot ID: {}'.format(bot.user.id))

@bot.command(pass_context=True)
async def commands(ctx):
    print('Help')
    #TODO: OUTPUT HELP
    # await ctx.send('Help')

@bot.command(pass_context=True)
async def join(ctx):
    await ctx.send("Bert is gay", tts=True)
    channel = ctx.message.author.voice.channel if ctx.author.voice else None
    if not channel:
        await ctx.send("You must be in a voice channel.")
        return

    try:
        print('TRYING TO CONNECT TO CHANNEL')
        await channel.connect()
    except:
        e = sys.exc_info()[0]
        print(e)
    else:
        print("Joined voice channel")
        await commands(ctx)

async def check_in_voice(ctx):
    if ctx.author.voice:
        if not ctx.voice_client:
            # If the bot is not in a voice channel, join the channel that the user is in
            channel = ctx.message.author.voice.channel
            await channel.connect()
    else:
        await ctx.send("You are not in a voice channel")
        raise RuntimeError('You are not in a voice channel')


def search_song(content, link = False):
    video_search = VideosSearch(content, limit=1)

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
    url = results['url']
    title = results['title']
    result_id = results['id']

    return Song(title, url, result_id)

async def add_to_song_queue(ctx, song):
    global songQueue
    songQueue.append(song)

    if len(songQueue) == 1 and not ctx.voice_client.is_playing():
        song = songQueue[0]
        # If there is only one song in the queue and no song is playing, play the song immediately
        ctx.voice_client.play(discord.FFmpegPCMAudio(song.url, **FFMPEG_OPTIONS), after=lambda e: play_next(ctx))
        await ctx.send(f'Playing {song.title}! 🎶')
    else:
        await ctx.send(f'Added {song.title} to the queue! 🎶')


@bot.command(pass_context=True)
async def playlist(ctx, *, content = False):

    await check_in_voice(ctx)

    # content = 'https://www.youtube.com/playlist?list=PLDIoUOhQQPlWt8OpaGG43OjNYuJ2q9jEN'

    url_template = "https://www.youtube.com/playlist?list="
    if not content:
        await ctx.send("Please provide a playlist URL: " . format(url_template))
        return

    if url_template not in content:
        await ctx.send(content + " is not a valid youtube playlist URL.")
        return

    try:
        ydl_opts = {
            'nocheckcertificate': True,
            "ignoreerrors": True,
            "quiet": True,
            "simulate": True,
            "allow_playlist_files" : False,
            'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
            'extract_flat': True
        }

        results = yt_dlp.YoutubeDL(ydl_opts).extract_info(content, download=False)

        for video in results['entries']:
            if not video:
                print("ERROR: Unable to get info. Continuing...")
                continue

            info = {
                "title": video['title'],
                'uploader': video['uploader'],
                "url": video['url'],
            }

            print(info)
            song = search_song(info["title"])
            await add_to_song_queue(ctx, song)
    except:
        e = sys.exc_info()[0]
        print(e)
        print(traceback.format_exc())
        await ctx.send("Something went wrong while processing your playlist.")

@bot.command(pass_context=True)
async def play(ctx, *, content):

    if isinstance(content, str) and len(content) > 0:
        await check_in_voice(ctx)

        # check if song is paused
        if ctx.voice_client is not None and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send('Resume playing track!')

        song = search_song(content)
        await add_to_song_queue(ctx, song)

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
        await ctx.send("Nothing to resume.")


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

@bot.command(pass_context=True)
async def reset(ctx):
    global songQueue
    await check_in_voice(ctx)
    songQueue = []
    await ctx.send('The queue has been cleared.')

@bot.command(pass_context=True)
async def shuffle(ctx):
    import random
    global songQueue
    await check_in_voice(ctx)
    random.shuffle(songQueue)
    await ctx.send('The queue has been shuffled.')

@bot.command(pass_context=True)
async def queue(ctx):
    global songQueue
    if len(songQueue) == 0:
        await ctx.send('The queue is currently empty.')
    else:
        q = '\n'.join([f'{i + 1}. {songQueue[i].title}' for i in range(len(songQueue))])
        await ctx.send(f'```Queue:\n{q}```')


@bot.command(pass_context=True)
async def skip(ctx):
    global songQueue
    if ctx.voice_client is not None and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        if len(songQueue) > 0:
            await ctx.send('Skipping to the next song in the queue.')
        else:
            await ctx.send('No more songs in the queue.')
    else:
        await ctx.send("I'm not currently playing anything.")


@bot.command(pass_context=True)
async def stop(ctx):
    global songQueue
    
    if ctx.voice_client is not None:
        songQueue = []
        await ctx.voice_client.disconnect()
        await ctx.send('Disconnected from the voice channel.')
    else:
        await ctx.send("I'm not currently connected to a voice channel.")

def get_lyrics(videoID):
    url = "https://youtubetranscript.com/?server_vid2=" + videoID
    r = requests.get(url)
    return r.text

@bot.command(pass_context=True)
async def lyrics(ctx):
    global songQueue
    if len(songQueue) == 0:
        await ctx.send('The queue is currently empty.')
    else:
        song = songQueue[0]
        xml_string = get_lyrics(song.id)

        # Parse the XML string
        root = ET.fromstring(xml_string)

        # Extract text from <text> elements
        text_elements = root.findall(".//text")

        final_string = ""
        # Iterate through the text elements and print their text content
        for text_element in text_elements:
            # print(text_element.text)
            final_string += text_element.text + "\n"
        if len(final_string) > 2000:
            await ctx.send(f'```Lyrics:\n{final_string[:1800]}```')
        else:
        # q = '\n'.join([f'{i + 1}. {queue_titles[i]}' for i in range(len(queue_list))])
            await ctx.send(f'```Lyrics:\n{final_string}```')


bot.run(token)
