import datetime
import logging
import traceback
from discord.ext import commands
import requests
import xml.etree.ElementTree as ET

from models.CommandCount import CommandCount
from sqlite.database import *
from bot_helpers import *

# @TODO: FIX PYTHON PACKAGES SPECIFICALLY DISCORD.PY
# EITHER USE MAIN BRANCH OF REPO OR WAIT FOR UPDATE OF PACKAGE (MAY NEED TO UPDATE OTHER PACKAGES) https://github.com/Rapptz/discord.py
# @ISSUE: https://github.com/Rapptz/discord.py/issues/10207

load_dotenv()
DEBUG = os.getenv("DEBUG") != '0'

if DEBUG:
    print("Debug Mode ON")

    logger = logging.getLogger('peewee')
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)

    token = os.environ['DEBUG_TOKEN']
    bot = commands.Bot(command_prefix='$', intents=discord.Intents.all())
else:
    token = os.environ['TOKEN']
    bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

songQueue = []

def except_hook(exctype, value, traceback):
    log_error([exctype, value])
    log_error(traceback)
    asyncio.get_event_loop().stop()
    if DEBUG:
        print('Stopping Bot...')
        die()
    else:
        print('Trigger standard Exception Hook.')
        sys.__excepthook__(exctype, value, traceback)
        print('Restarting bot...')
        # restart script
        os.execv(sys.executable, ['python'] + sys.argv)

sys.excepthook = except_hook


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    error_type = type(error).__name__
    embed = discord.Embed(title=error_type, color=discord.Color.red())
    error_data = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    log_error(error_data)
    if DEBUG:
        embed.description = f"Traceback:\n```py\n{error_data[:1000]}\n```"
        await ctx.send(embed=embed)
        print('Stopping Bot...')
        die()
    else:
        await ctx.send('❌ An Error has Occurred!💀')

    if ctx.voice_client is not None:
        await ctx.voice_client.disconnect(force=True)

    # await bot.on_command_error(ctx, error)

@bot.event
async def on_ready():
    init_logs()
    create_db()
    global songQueue
    print('Connected to bot: {}'.format(bot.user.name))
    print('Bot ID: {}'.format(bot.user.id))


# Dup commands still happening
@bot.event
async def on_message(message):
    try:
        command = message.content.split()[0].strip(bot.command_prefix)
    except IndexError:
        print(message.content)
        return

    if message.author.bot:
        return

    if GlobalSettings.CURRENT_USER is None:
        establish_globals(message.author)
        command_count, created = CommandCount.get_or_create(command=command, user_id=GlobalSettings.CURRENT_USER.id , defaults={'counter': 1})
        if not created:
            command_count.counter += 1
            command_count.date_last_action = datetime.now()
            command_count.save()

    await bot.process_commands(message)

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
        init_logs()

async def check_in_voice(ctx):
    if ctx.author.voice:
        if not ctx.voice_client:
            # If the bot is not in a voice channel, join the channel that the user is in
            channel = ctx.message.author.voice.channel
            await channel.connect()
    else:
        await ctx.send("You are not in a voice channel")
        raise RuntimeError('You are not in a voice channel')


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
        print(results)
        die()
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
            die()
            song = search_song(info["title"])
            await add_to_song_queue(ctx, song)
    except:
        e = sys.exc_info()[0]
        print(e)
        print(traceback.format_exc())
        await ctx.send("Something went wrong while processing your playlist.")

@bot.command(pass_context=True)
async def play(ctx, *, content = None):

    if isinstance(content, str) and len(content) > 0:
        await check_in_voice(ctx)

        # check if song is paused
        if ctx.voice_client is not None and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send('Resume playing track!')

        song, created = search_song(content)

        if created:
            await ctx.send(f'Saved 🎶{song.title}🎶 to music library!📖')

        await add_to_song_queue(ctx, song.id)

    elif ctx.voice_client is not None and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send('Resume playing track!')
    elif SongQueue.queue_length() > 0:
        await check_in_voice(ctx)
        if ctx.voice_client is not None:
            await ctx.send("Starting off where we left off in the Queue!")
            await play_queue(ctx)
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

@bot.command(pass_context=True)
async def reset(ctx):
    await check_in_voice(ctx)
    deleted = SongQueue.clear()
    await ctx.send('All ' + str(deleted) + ' items deleted from Queue!')

@bot.command(pass_context=True)
async def shuffle(ctx):
    import random
    global songQueue
    await check_in_voice(ctx)
    random.shuffle(songQueue)
    await ctx.send('The Queue has been shuffled.')

@bot.command(pass_context=True)
async def queue(ctx):
    if SongQueue.queue_length() == 0:
        await ctx.send('The Queue is currently empty.')
    else:
        song_queue = SongQueue.songs_in_queue()
        output = ''
        for position, title in song_queue.items():
            output += f'{str(position)}. {title}\n'
        await ctx.send(f'```Queue:\n{output}```')


@bot.command(pass_context=True)
async def skip(ctx):
    if ctx.voice_client is not None and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        if SongQueue.queue_length() > 0:
            await ctx.send('Skipping to the next song in the queue.')
        else:
            await ctx.send('No more songs in the queue.')
    else:
        await ctx.send("I'm not currently playing anything.")


@bot.command(pass_context=True)
async def stop(ctx):
    if ctx.voice_client is not None:
        SongQueue.clear()
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
    if SongQueue.queue_length() == 0:
        await ctx.send('The queue is currently empty.')
    else:
        song = SongQueue.get_last_song()
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

@bot.command(pass_context=True)
async def kys(ctx, name = None):
    user = Users.get(discord_id = ctx.author.id)

    if name is None or '@' not in name:
        discord_id = GlobalSettings.CURRENT_USER.discord_id
        if user.discord_id != GlobalSettings.CURRENT_USER.discord_id:
            discord_id = user.discord_id
        name = '@' + str(discord_id)

    await ctx.send("☠️💀KILL YOUR SELF " + name + "!!!💀☠️")

bot.run(token)
