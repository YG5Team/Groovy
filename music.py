from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import discord
from discord.ext import commands

from db import increment_song_play_count, is_enabled as db_enabled

log = logging.getLogger("groovy")


# FFmpeg options used for audio playback
FFMPEG_BEFORE_OPTS = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
FFMPEG_OPTS = "-vn"


@dataclass
class Track:
    title: str
    stream_url: str
    webpage_url: str
    song_id: Optional[int] = None


class GuildMusic:
    def __init__(self, guild: discord.Guild):
        self.guild = guild
        self.queue: asyncio.Queue[Track] = asyncio.Queue()
        self.player_task: Optional[asyncio.Task] = None
        self.now_playing: Optional[Track] = None
        self.text_channel: Optional[discord.TextChannel] = None
        self.override_end_status: Optional[str] = None  # 'skipped' | 'stopped' | 'error'

    async def ensure_voice(self, ctx: commands.Context) -> discord.VoiceClient:
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError("Join a voice channel first.")
        channel = ctx.author.voice.channel
        if ctx.voice_client:
            if ctx.voice_client.channel != channel:
                await ctx.voice_client.move_to(channel)
            return ctx.voice_client
        return await channel.connect(self_deaf=True)

    def start_player_if_needed(self, vc: discord.VoiceClient):
        if self.player_task and not self.player_task.done():
            return
        self.player_task = asyncio.create_task(self._player_loop(vc))

    async def _player_loop(self, vc: discord.VoiceClient):
        try:
            while True:
                track = await self.queue.get()
                self.now_playing = track
                source = discord.FFmpegPCMAudio(
                    track.stream_url,
                    before_options=FFMPEG_BEFORE_OPTS,
                    options=FFMPEG_OPTS,
                )
                vc.play(source)
                if self.text_channel:
                    await self._safe_send(self.text_channel, f"Now playing: {track.title}")
                # Wait until the track finishes
                while vc.is_playing() or vc.is_paused():
                    await asyncio.sleep(1)
                # DB: finalize status
                try:
                    if db_enabled():
                        if track.song_id:
                            await increment_song_play_count(track.song_id)
                except Exception:
                    log.exception("Failed to increment play_count")
                self.now_playing = None
                self.override_end_status = None
                # If queue empty, break and end task
                if self.queue.empty():
                    break
        except Exception as e:
            log.exception("Player loop error: %s", e)
            if self.text_channel:
                await self._safe_send(self.text_channel, "Playback error. Skipping.")
            self.override_end_status = "error"
        finally:
            # Optionally disconnect after idle
            await asyncio.sleep(5)
            if vc and vc.is_connected() and not vc.is_playing() and self.queue.empty():
                await vc.disconnect(force=True)

    @staticmethod
    async def _safe_send(ch: discord.TextChannel, msg: str):
        try:
            await ch.send(msg)
        except Exception:
            pass
