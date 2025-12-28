from __future__ import annotations

import os
import asyncio
import logging
from typing import Optional, Dict

import discord
from discord.ext import commands
from dotenv import load_dotenv

from db import (
    init_pool,
    close_pool,
    upsert_song,
    is_enabled as db_enabled,
    get_top_songs,
)
from bot_helpers import fetch_track, get_guild_music
from music import Track

from aiohttp import web

load_dotenv()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("groovy")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    log.info("Logged in as %s", bot.user)
    # Initialize DB pool on startup
    await init_pool()

@bot.command(name="play", help="Play audio from a URL or search. Usage: !play <url or search terms>")
async def play(ctx: commands.Context, *, query: str):
    gm = get_guild_music(ctx.guild)
    gm.text_channel = ctx.channel
    vc = await gm.ensure_voice(ctx)

    try:
        async with ctx.typing():
            track = await fetch_track(query)
    except Exception:
        await ctx.send("Failed to get audio. Try another query.")
        return

    # DB: upsert song, then enqueue. We'll increment play_count when finished.
    try:
        if db_enabled():
            song_id = await upsert_song(track.title, track.webpage_url, track.stream_url)
            track.song_id = song_id
    except Exception:
        log.exception("Failed to log play to DB")

    await gm.queue.put(track)
    await ctx.send(f"Queued: {track.title}")
    gm.start_player_if_needed(vc)

@bot.command(name="skip", help="Skip the current track.")
async def skip(ctx: commands.Context):
    if not ctx.voice_client or not ctx.voice_client.is_connected():
        await ctx.send("Not connected.")
        return
    if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
        ctx.voice_client.stop()
        gm = get_guild_music(ctx.guild)
        gm.override_end_status = "skipped"
        await ctx.send("Skipped.")
    else:
        await ctx.send("Nothing is playing.")

@bot.command(name="stop", help="Stop and clear the queue, then disconnect.")
async def stop(ctx: commands.Context):
    gm = get_guild_music(ctx.guild)
    # Clear queue
    while not gm.queue.empty():
        try:
            gm.queue.get_nowait()
            gm.queue.task_done()
        except asyncio.QueueEmpty:
            break
    if ctx.voice_client and ctx.voice_client.is_connected():
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect(force=True)
    await ctx.send("Stopped and disconnected.")

@bot.command(name="queue", help="Show the current queue.")
async def queue(ctx: commands.Context):
    gm = get_guild_music(ctx.guild)
    now = gm.now_playing
    # Snapshot pending items without consuming the queue
    pending = list(gm.queue._queue)  # type: ignore[attr-defined]

    if not now and not pending:
        await ctx.send("Queue is empty.")
        return

    lines = []
    if now:
        lines.append(f"Now playing: {now.title}")

    if pending:
        for i, t in enumerate(pending, start=1):
            lines.append(f"{i}. {t.title}")

    # Send in chunks to respect Discord's 2000 character limit
    MAX = 2000
    buf = ""
    for line in lines:
        if len(buf) + len(line) + 1 > MAX:
            await ctx.send(buf)
            buf = line
        else:
            buf = f"{buf}\n{line}" if buf else line
    if buf:
        await ctx.send(buf)

@bot.command(name="lyrics", help="Fetch lyrics for the currently playing song.")
async def lyrics(ctx: commands.Context):
    # Example: !lyrics
    await ctx.send("Not implemented yet.")

@bot.command(name="kys", help="Tell someone to 'kys'. Usage: !kys @user")
async def kys(ctx: commands.Context):
    # Example: !kys @user
    await ctx.send("Not implemented yet.")

@bot.command(name="top", help="Show top played songs. Usage: !top songs <N> Optional:[q|queue]")
async def top(ctx: commands.Context, n: Optional[int] = 10, queue: Optional[str] = None):
    if not db_enabled():
        await ctx.send("Database not configured.")
        return

    try:
        rows = await get_top_songs(n)
    except Exception:
        log.exception("Failed to fetch top songs")
        await ctx.send("Failed to fetch top songs.")
        return

    if not rows:
        await ctx.send("No song stats available.")
        return

    lines = []
    for i, (title, plays, webpage_url) in enumerate(rows, start=1):
        lines.append(f"{i}. {title} — {plays} plays")

    # Send in chunks to respect Discord's 2000 character limit
    MAX = 2000
    buf = ""
    for line in lines:
        if len(buf) + len(line) + 1 > MAX:
            await ctx.send(buf)
            buf = line
        else:
            buf = f"{buf}\n{line}" if buf else line
    if buf:
        await ctx.send(buf)

    if queue:
        gm = get_guild_music(ctx.guild)
        gm.text_channel = ctx.channel
        try:
            vc = await gm.ensure_voice(ctx)
        except commands.CommandError as e:
            await ctx.send(str(e))
            return

        queued = 0
        try:
            async with ctx.typing():
                for row in rows:
                    title = row[0]  # title is the first element
                    try:
                        track = await fetch_track(title)
                        await gm.queue.put(track)
                        queued += 1
                    except Exception:
                        log.exception("Failed to fetch track for title: %s", title)
            if queued:
                await ctx.send(f"Queued top {queued} songs.")
                gm.start_player_if_needed(vc)
            else:
                await ctx.send("No songs queued.")
        except Exception:
            log.exception("Failed to queue top songs")
            await ctx.send("Failed to queue top songs.")

# catch all for unknown commands and errors
@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Unknown command.")
    else:
        log.error("Command error: %s", error)

async def handle_embed_request(request):
    data = await request.json()
    channel_id = int(data["channel_id"])
    embed_data = data["embed"]
    
    embed = discord.Embed.from_dict(embed_data)
    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send(embed=embed)
        return web.Response(text="Embed sent!")
    return web.Response(status=404, text="Channel not found")

async def handle_message_request(request):
    data = await request.json()
    channel_id = int(data["channel_id"])
    message_content = data["message"]
    
    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send(message_content)
        return web.Response(text="Message sent!")
    return web.Response(status=404, text="Channel not found")

async def run_webserver():
    app = web.Application()
    app.add_routes([web.post('/send_embed', handle_embed_request)])
    app.add_routes([web.post('/send_message', handle_message_request)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 8080)
    await site.start()


async def main():
    token = os.getenv("DEBUG_TOKEN")
    if not token:
        raise SystemExit("Set DEBUG_TOKEN environment variable.")
    try:
        await asyncio.gather(bot.start(token), run_webserver())
    finally:
        # Ensure DB pool closes on shutdown
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(close_pool())
            else:
                loop.run_until_complete(close_pool())
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())
