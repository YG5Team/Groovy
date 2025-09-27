from datetime import datetime
import asyncio
from typing import Tuple, Optional, Dict

import discord
import yt_dlp

from helpers import *

from music import Track, GuildMusic

FFMPEG_OPTIONS = {
	'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
	'options': '-vn',
}

# yt-dlp options for extracting stream info
YTDLP_OPTS = {
	"format": "bestaudio/best",
	"quiet": True,
	"noplaylist": True,
	"default_search": "ytsearch",
	"skip_download": True,
	"source_address": "0.0.0.0",
	"extractor_args": {
		"youtube": {
			"player_client": ["default", "-tv_simply"],
		},
	},
}


async def fetch_track(query: str) -> Track:
	def _extract() -> Track:
		with yt_dlp.YoutubeDL(YTDLP_OPTS) as ydl:
			info = ydl.extract_info(query, download=False)
			if "entries" in info:
				info = info["entries"][0]
			title = info.get("title", "Unknown")
			webpage_url = info.get("webpage_url") or info.get("original_url") or query
			stream_url = info["url"]
			return Track(title=title, stream_url=stream_url, webpage_url=webpage_url)

	return await asyncio.to_thread(_extract)


# Per-guild music registry
_music: Dict[int, GuildMusic] = {}


def get_guild_music(guild: discord.Guild) -> GuildMusic:
	gm = _music.get(guild.id)
	if not gm:
		gm = GuildMusic(guild)
		_music[guild.id] = gm
	return gm
