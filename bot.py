import discord
from discord.ext import commands
from youtubesearchpython import VideosSearch
import yt_dlp
from dotenv import load_dotenv
import os


load_dotenv()
token = os.getenv("token")

# intents = discord.Intents.all()
bot = commands.Bot()

queue = []
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn'}

@bot.slash_command(name="play", guild_ids=['759520511553830913', '729233019034009680']) #Add the guild ids in which the slash command will appear. If it should be in all, remove the argument, but note that it will take some time (up to an hour) to register the command if it's for all guilds.
async def play(ctx, search: str):
    voice_channel = ctx.author.voice.channel
    voice_client = ctx.voice_client
    if ctx.voice_client is None:
        voice_client = await voice_channel.connect()
    else:
        await ctx.voice_client.move_to(voice_channel)

    videosSearch = VideosSearch(search, limit = 1)

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

    if not voice_client.is_playing():
        # if there is no song playing, play the requested song immediately
        voice_client.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS))
        print(f'Playing {search}!')
        await ctx.send(f'Playing {search}!')
    else:
        queue.append(url)
        await ctx.send(f'Added {search} to the queue!')
    
    # await ctx.send(f'Playing {search}!')

@bot.slash_command(name="queue", guild_ids=['759520511553830913', '729233019034009680'])
async def show_queue(ctx):
    global queue
    if len(queue) == 0:
        await ctx.send('The queue is currently empty.')
    else:
        queue_list = '\n'.join([f'{i+1}. {queue[i]}' for i in range(len(queue))])
        await ctx.send(f'```Queue:\n{queue_list}```')

@bot.slash_command(name="skip", guild_ids=['759520511553830913', '729233019034009680'])
async def skip(ctx):
    global queue
    if ctx.voice_client is not None and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        if len(queue) > 0:
            # if there are songs in the queue, play the next one
            next_song = queue.pop(0)
            ctx.voice_client.play(discord.FFmpegPCMAudio(next_song, **FFMPEG_OPTIONS))
            await ctx.send('Skipping to the next song in the queue.')
        else:
            await ctx.send('No more songs in the queue.')
    else:
        await ctx.send("I'm not currently playing anything.")

@bot.slash_command(name="stop", guild_ids=['759520511553830913', '729233019034009680'])
async def stop(ctx):
    global queue
    queue = []
    if ctx.voice_client is not None:
        await ctx.voice_client.disconnect()
        await ctx.send('Disconnected from the voice channel.')
    else:
        await ctx.send("I'm not currently connected to a voice channel.")

bot.run(token)
