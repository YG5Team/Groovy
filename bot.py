import datetime
import logging
import traceback
from discord.ext import commands
import requests
import xml.etree.ElementTree as ET

from models.CommandCount import CommandCount
from sqlite.database import *
from bot_helpers import *

"""
@FIXME: ADDING TO QUEUE AND SONG SEARCHING NEED TO BE UPDATED TO A THREAD OR ASYNC
        TAKE TOO LONG AND PREVENT OTHER COMMANDS
"""

load_dotenv()
DEBUG = os.getenv("DEBUG") != '0'

if DEBUG:
    debug("Debug Mode ON")

    logger = logging.getLogger('peewee')
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)

    token = os.environ['DEBUG_TOKEN']
    bot = commands.Bot(command_prefix='$', intents=discord.Intents.all())
else:
    token = os.environ['TOKEN']
    bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

def except_hook(exctype, value, traceback):
    print('Trigger standard Exception Hook.')
    log_error([exctype, value])
    log_error(traceback)
    asyncio.get_event_loop().stop()
    if DEBUG:
        debug('Stopping Bot...')
        # die()
    else:
        sys.__excepthook__(exctype, value, traceback)
        print('Restarting bot...')
        # restart script
        os.execv(sys.executable, ['python'] + sys.argv)

sys.excepthook = except_hook


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    GlobalSettings.LAST_ERROR = error
    error_type = type(error).__name__
    embed = discord.Embed(title=error_type, color=discord.Color.red())
    error_data = format_error(error)
    log_error(error_data)
    if DEBUG:
        embed.description = f"Traceback:\n```py\n{error_data[:1000]}\n```"
        await ctx.send(embed=embed)
        debug('Stopping Bot...')
        # die()
    else:
        await ctx.send('❌ An Error has Occurred!💀\n Thanks ' + get_discord_tag() + '...')

    if ctx.voice_client is not None:
        await ctx.voice_client.disconnect(force=True)

    # await bot.on_command_error(ctx, error)

@bot.event
async def on_ready():
    init_logs()
    create_db()
    global LAST_ERROR
    print('Connected to bot: {}'.format(bot.user.name))
    print('Bot ID: {}'.format(bot.user.id))


# Dup output still happening
@bot.event
async def on_message(message):
    try:
        input_command = message.content.split()[0].strip(bot.command_prefix)
    except IndexError:
        print(message.content)
        return

    if message.author.bot:
        return

    #Should always set
    establish_globals(message.author)
    for command in bot.commands:
        if command.name == input_command:
            command_count, created = CommandCount.get_or_create(command=input_command, user_id=GlobalSettings.CURRENT_USER.id , defaults={'counter': 1})
            if not created:
                command_count.counter += 1
                command_count.date_last_action = datetime.now()
                command_count.save()
            break

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

async def check_in_voice(ctx, join = True):
    if ctx.author.voice:
        if not ctx.voice_client and join:
            # If the bot is not in a voice channel, join the channel that the user is in
            channel = ctx.message.author.voice.channel
            await channel.connect()
    else:
        await ctx.send("You are not in a voice channel. You cannot reset the Queue.")
        # raise RuntimeError('You are not in a voice channel')


@bot.command(pass_context=True)
async def yt_playlist(ctx, *, content = None):

    await check_in_voice(ctx)

    #For testing purposes. DO NOT UNCOMMENT
    # content = 'https://www.youtube.com/playlist?list=PLDIoUOhQQPlWt8OpaGG43OjNYuJ2q9jEN'

    is_valid, content = YouTubePlaylists.validate_url(content)

    if not is_valid:
        await ctx.send(content)
        return

    url = base64_encode(content)
    new_songs = 0
    youtube_playlist = YouTubePlaylists.select().where(YouTubePlaylists.url == url).get_or_none()

    if youtube_playlist:
        created = False
        if youtube_playlist.expected_num_items != YouTubePlaylistSongs.select().where(YouTubePlaylistSongs.youtube_playlist == youtube_playlist.id).count():
            new_songs, youtube_playlist, created = YouTubePlaylists.save_youtube_playlist(content)
    else:
        new_songs, youtube_playlist, created = YouTubePlaylists.save_youtube_playlist(content)

    if isinstance(youtube_playlist, str):
        await ctx.send(youtube_playlist)
    else:
        if created:
            await ctx.send(f'Saved 🎶{youtube_playlist.title}🎶 to YouTube Playlist library!📖')

        if new_songs > 0:
            await ctx.send(f'Saved {new_songs} new song(s) to music library!🎶📖')

        await ctx.send(f'Adding songs from YouTube Playlist 🎶{youtube_playlist.title}🎶 to Queue!')
        await add_youtube_playlist_to_queue(ctx, youtube_playlist)
        count = youtube_playlist.song_count()
        await ctx.send(f'Finished adding {str(count)} songs from YouTube Playlist 🎶{youtube_playlist.title}🎶 to Queue!')



@bot.command(pass_context=True)
async def play(ctx, *, content = None):

    if isinstance(content, str) and len(content) > 0:
        await check_in_voice(ctx)

        # check if song is paused
        if ctx.voice_client is not None and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send('Resume playing track!')

        song, created = Songs.save_song(content)

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
        await ctx.send("I'm not currently playing anything and there is nothing in the Queue. Type what you want to play!")


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
    if SongQueue.queue_length() > 0:
        await check_in_voice(ctx, False)
        deleted = SongQueue.clear()
        await ctx.send('All ' + str(deleted) + ' items deleted from Queue!')
    else:
        await ctx.send("The Queue is empty. Type what you want to play!")

@bot.command(pass_context=True)
async def shuffle(ctx):
    await check_in_voice(ctx)
    SongQueue.shuffle()
    await ctx.send('🎲The Queue has been shuffled.🎲')

@bot.command(pass_context=True)
async def queue(ctx, limit = ''):
    if SongQueue.queue_length() == 0:
        await ctx.send('The Queue is currently empty.')
    else:
        limit_message = ''
        query = SongQueue.get_queue()
        if limit.isnumeric():
            query = query.limit(int(limit))
            limit_message = f' (FIRST {limit}) '

        await ctx.send(f'```The following are currently in the Queue{limit_message}:```')
        count = 0
        for item in query.execute():
            output = f'{str(item.position)}. [ID: {item.song.id}] {item.song.title}\n'
            await ctx.send(f'```{output}```')
            count += 1
            if limit.isnumeric() and count >= int(limit):
                break


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
        song = SongQueue.get_first_song()
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
async def kys(ctx, content = None):
    name = content
    message = ''
    if name is not None and '@' not in name:
        target_user = Users.select(Users.discord_id).where((Users.name == name) | (Users.global_name == name) ).get_or_none()
        if target_user is not None:
            name = get_discord_tag(target_user.discord_id)
        else:
            message = "I don't know who `" + content + "` is, so...\n"

    author = Users.get(discord_id=ctx.author.id)
    if name is None or '@' not in name:
        if CommandCount.select().count() == 1:
            message = 'First Time⁉️\n'
        discord_id = GlobalSettings.CURRENT_USER.discord_id
        if author.discord_id != GlobalSettings.CURRENT_USER.discord_id:
            establish_globals(ctx.author)
            discord_id = author.discord_id
        name = get_discord_tag(discord_id)

    #maybe play emote
    await ctx.send(message + "☠️💀 KILL YOUR SELF " + name + "!!! 💀☠️")

@bot.command(pass_context=True)
async def error(ctx):
    if GlobalSettings.LAST_ERROR is None:
        await ctx.send('No errors to report.')
        return

    last_error = GlobalSettings.LAST_ERROR

    error_type = type(last_error).__name__
    text = f'"{GlobalSettings.CURRENT_USER.name}" reported the following error: [{error_type}]'
    embed = discord.Embed(title=text, color=discord.Color.red())
    error_data = format_error(last_error)
    embed.description = f"Traceback:\n```py\n{error_data[:2000]}\n```"

    await ctx.send('Sending last error to key personnel.')
    dev_list = os.getenv("ADMIN_LIST")
    if dev_list is None:
        await ctx.send('Key personnel IDs are not defined.')
    else:
        devs = dev_list.split(',')
        for dev_id in devs:
            user = bot.get_user(int(dev_id))
            await user.send(embed=embed)
        await ctx.send('Error reported.')

bot.run(token)
