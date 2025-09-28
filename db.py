import os
import asyncio
import logging
from typing import Optional, Tuple

import aiomysql

log = logging.getLogger("groovy.db")

_pool: Optional[aiomysql.Pool] = None
_init_lock = asyncio.Lock()
_enabled = True


def _cfg() -> Tuple[str, int, str, str, Optional[str]]:
    host = os.getenv("MYSQL_HOST") or "localhost"
    port = int(os.getenv("MYSQL_PORT") or 3306)
    user = os.getenv("MYSQL_USER") or "root"
    password = os.getenv("MYSQL_PASSWORD") or ""
    database = os.getenv("MYSQL_DATABASE")
    return host, port, user, password, database


async def init_pool() -> None:
    global _pool, _enabled
    if _pool is not None or not _enabled:
        return
    async with _init_lock:
        if _pool is not None or not _enabled:
            return
        host, port, user, password, database = _cfg()
        try:
            # If database isn't provided, we'll run without DB
            if not database:
                _enabled = False
                log.warning("MySQL disabled: MYSQL_DATABASE not set. Skipping DB logging.")
                return
            _pool = await aiomysql.create_pool(
                host=host,
                port=port,
                user=user,
                password=password,
                db=database,
                autocommit=True,
                minsize=1,
                maxsize=5,
                charset="utf8mb4",
                use_unicode=True,
            )
            await ensure_schema()
            log.info("MySQL pool initialized and schema ensured")
        except Exception as e:
            _enabled = False
            log.exception("Failed to initialize MySQL: %s. DB logging disabled.", e)


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        await _pool.wait_closed()
        _pool = None


def is_enabled() -> bool:
    return _enabled and _pool is not None


async def ensure_schema() -> None:
    if not is_enabled():
        return
    assert _pool is not None
    create_songs = (
        """
        CREATE TABLE IF NOT EXISTS songs (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            title VARCHAR(512) NOT NULL,
            webpage_url VARCHAR(1024) NOT NULL,
            stream_url TEXT NOT NULL,
            play_count BIGINT UNSIGNED NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY uq_webpage_url (webpage_url(255))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
    )
    async with _pool.acquire() as conn:  # type: ignore
        async with conn.cursor() as cur:
            await cur.execute(create_songs)
            # Ensure columns exist for existing installations
            # songs.play_count
            await cur.execute(
                """
                SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME='songs' AND COLUMN_NAME='play_count'
                """
            )
            (exists_play_count,) = await cur.fetchone()
            if not exists_play_count:
                await cur.execute(
                    "ALTER TABLE songs ADD COLUMN play_count BIGINT UNSIGNED NOT NULL DEFAULT 0 AFTER stream_url"
                )


async def upsert_song(title: str, webpage_url: str, stream_url: str) -> Optional[int]:
    if not is_enabled():
        return None
    assert _pool is not None
    sql_insert = (
        """
        INSERT INTO songs (title, webpage_url, stream_url)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE title = VALUES(title), stream_url = VALUES(stream_url)
        """
    )
    sql_select = "SELECT id FROM songs WHERE webpage_url = %s"
    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql_insert, (title, webpage_url, stream_url))
            await cur.execute(sql_select, (webpage_url,))
            row = await cur.fetchone()
            return int(row[0]) if row else None


async def increment_song_play_count(song_id: Optional[int]) -> Optional[int]:
    if not is_enabled() or not song_id:
        return None
    assert _pool is not None
    async with _pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("UPDATE songs SET play_count = play_count + 1 WHERE id = %s", (song_id,))
            await cur.execute("SELECT play_count FROM songs WHERE id = %s", (song_id,))
            row = await cur.fetchone()
            return int(row[0]) if row else None

async def get_top_songs(limit: int) -> list[tuple[str, str, int]]:
    if not is_enabled():
        return []
    assert _pool is not None
    limit = max(1, min(int(limit), 100))
    sql = """
        SELECT title, play_count, webpage_url
        FROM songs
        ORDER BY play_count DESC, id DESC
        LIMIT %s
    """
    async with _pool.acquire() as conn:  # type: ignore
        async with conn.cursor() as cur:
            await cur.execute(sql, (limit,))
            rows = await cur.fetchall()
            return [(r[0], int(r[1]), r[2]) for r in rows]
