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
)
from bot_helpers import fetch_track, get_guild_music
from music import Track

load_dotenv()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("groovy")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="$", intents=intents)


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
    # Example: !queue
    await ctx.send("Not implemented yet.")

@bot.command(name="lyrics", help="Fetch lyrics for the currently playing song.")
async def lyrics(ctx: commands.Context):
    # Example: !lyrics
    await ctx.send("Not implemented yet.")

@bot.command(name="kys", help="Tell someone to 'kys'. Usage: !kys @user")
async def kys(ctx: commands.Context):
    # Example: !kys @user
    await ctx.send("Not implemented yet.")

@bot.command(name="top", help="Show top played songs. Usage: !top songs <N>")
async def top(ctx: commands.Context):
    # Example: !top songs 10
    await ctx.send("Not implemented yet.")

# catch all for unknown commands and errors
@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Unknown command.")
    else:
        log.error("Command error: %s", error)

def main():
    token = os.getenv("DEBUG_TOKEN")
    if not token:
        raise SystemExit("Set DEBUG_TOKEN environment variable.")
    try:
        bot.run(token)
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
    main()