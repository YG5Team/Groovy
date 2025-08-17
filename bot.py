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

load_dotenv()
token = os.environ['TOKEN']
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

# get args
if len(sys.argv) == 2:
    if sys.argv[1] == "debug":
        token = os.environ['TOKEN_DEBUG']
        bot = commands.Bot(command_prefix='@', intents=discord.Intents.all())

songQueue = []
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

@bot.event
async def on_ready():
    print('Connected to bot: {}'.format(bot.user.name))
    print('Bot ID: {}'.format(bot.user.id))


@bot.command(pass_context=True)
async def play(ctx, *, content):
    global songQueue

    if isinstance(content, str) and len(content) > 0:
        if (ctx.author.voice):
            if (not ctx.voice_client):
                # If the bot is not in a voice channel, join the channel that the user is in
                channel = ctx.message.author.voice.channel
                await channel.connect()
        else:
            await ctx.send("You are not in a voice channel")
            return

        # check if song is paused
        if ctx.voice_client is not None and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send('Resume playing track!')

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

        results = yt_dlp.YoutubeDL(ydl_opts).extract_info(link, download=False)
        url = results['url']
        print("after url")
        title = results['title']
        print("after title")
        id = results['id']
        print("after Id")
        song = Song(title, url, id)

        songQueue.append(song)

        if len(songQueue) == 1 and not ctx.voice_client.is_playing():
            song = songQueue[0]
            # If there is only one song in the queue and no song is playing, play the song immediately
            ctx.voice_client.play(discord.FFmpegPCMAudio(song.url, **FFMPEG_OPTIONS), after=lambda e: play_next(ctx))
            await ctx.send(f'Playing {song.title}! 🎶')
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
async def queue(ctx):
    global songQueue
    await ctx.send("Bert is gay", tts=True)
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

        finalString = ""
        # Iterate through the text elements and print their text content
        for text_element in text_elements:
            # print(text_element.text)
            finalString += text_element.text + "\n"
        if len(finalString) > 2000:
            await ctx.send(f'```Lyrics:\n{finalString[:1800]}```')
        else:
        # q = '\n'.join([f'{i + 1}. {queue_titles[i]}' for i in range(len(queue_list))])
            await ctx.send(f'```Lyrics:\n{finalString}```')


bot.run(token)
