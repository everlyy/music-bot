from config import *
from playlists.common import Playlist
import asyncio
import dataclasses
import discord
import lastfm
import os
import playlists
import random
import time
import tinytag

@dataclasses.dataclass
class Metadata:
    title: (str | None)
    artist: (str | None)
    album: (str | None)
    album_artist: (str | None)
    duration: float

class MusicBot(discord.Client):
    def __init__(self, lfm: lastfm.LastFM, lfmsm: lastfm.LastFMSessionManager):
        super().__init__(intents=discord.Intents.default())
        self.tree = discord.app_commands.CommandTree(self)
        self.playing: bool = False
        self.lfm = lfm
        self.lfmsm = lfmsm
        self.track: (str | None) = None

        self._vc: discord.VoiceClient
        self._skip: bool = False
        self.playlists: list[Playlist] = []
        self._scrobble_queue: list[tuple[str, bool, Metadata]] = []

    async def scrobbler(self):
        while True:
            while len(self._scrobble_queue) > 0:
                user_id, scrobble, metadata = self._scrobble_queue.pop(0)
                session = self.lfmsm.get_session(user_id)
                if session is None:
                    print(f"Couldn't find last.fm session key for {user_id}")
                    continue

                name, session_key = session

                if metadata.artist is None or metadata.title is None:
                    print(f"Not scrobbling for {user_id} ({name}) because there's not artist or title field")
                    continue

                print(f"Scrobbling {metadata} for {name} ({scrobble=})")

                if scrobble:
                    await self.lfm.track_scrobble(
                        track=metadata.title,
                        artist=metadata.artist,
                        album=metadata.album,
                        album_artist=(
                            metadata.artist
                            if metadata.album_artist is None else
                            metadata.album_artist
                        ),
                        timestamp=int(time.time()),
                        session_key=session_key
                    )
                else:
                    await self.lfm.track_update_now_playing(
                        track=metadata.title,
                        artist=metadata.artist,
                        album=metadata.album,
                        album_artist=(
                            metadata.artist
                            if metadata.album_artist is None else
                            metadata.album_artist
                        ),
                        session_key=session_key
                    )

            await asyncio.sleep(5)

    async def on_ready(self):
        print(f"Syncing command tree")
        #await self.tree.sync()

        print(f"Reloading playlists")
        self.reload_playlists()

        print(f"Initializing last.fm scrobbler")
        self.lfm.init_session()
        self.loop.create_task(self.scrobbler())

        print(f"Commands:")
        for item in self.tree.walk_commands():
            if isinstance(item, discord.app_commands.Group):
                print(f" {item.name}:")
                for cmd in item.walk_commands():
                    assert isinstance(cmd, discord.app_commands.Command)
                    print(f"  - {cmd.name}")
            else:
                if item.parent is not None:
                    continue
                print(f" - {item.name}")

        print(f"Have {len(self.playlists)} playlist(s)")
        for playlist in self.playlists:
            print(f" - {playlist.name} ({len(playlist.tracks)} track(s))")

        print(f"Bot ready")

    def find_playlist_by_name(self, playlist_name: str) -> (Playlist | None):
        for playlist in self.playlists:
            if playlist.name == playlist_name:
                return playlist

        return None

    def reload_playlists(self) -> None:
        self.playlists = playlists.parse_all_playlists(playlists.SearchPaths(
            xspf_path=PLAYLISTS_PATH,
            collection_path=COLLECTION_PATH
        ))

    def get_metadata(self, track: str) -> (Metadata | None):
        tag = tinytag.TinyTag.get(track)
        assert tag.duration is not None # Not sure why there wouldn't be a duration
        metadata = Metadata(tag.title, tag.artist, tag.album, tag.albumartist, tag.duration)
        return metadata

    async def dj(self, playlist: Playlist, channel: discord.VoiceChannel, updates: discord.TextChannel):
        while self.playing:
            self.track = random.choice(playlist.tracks)
            self._vc.play(discord.FFmpegOpusAudio(self.track, bitrate=256))

            play_start = time.time()
            scrobbled = False

            metadata = self.get_metadata(self.track)

            if metadata is not None:
                await updates.send(f"Now playing {metadata.title} by {metadata.artist}")
                for member in channel.members:
                    if member.id != self.application_id:
                        self._scrobble_queue.append((str(member.id), False, metadata))
            else:
                await updates.send(f"Now playing `{self.track}`\n-# This track will not scrobble because it does not have any metadata")

            while self._vc.is_playing():
                if self._skip:
                    self._vc.stop()
                    self._skip = False
                    break

                if metadata is not None and not scrobbled and (time.time() - play_start) > (metadata.duration * 0.5):
                    for member in channel.members:
                        if member.id != self.application_id:
                            self._scrobble_queue.append((str(member.id), True, metadata))

                    scrobbled = True

                await asyncio.sleep(1)

    async def play(self, playlist: Playlist, channel: discord.VoiceChannel, updates: discord.TextChannel):
        if self.playing:
            return

        self.playing = True
        self._vc = await channel.connect()
        self.loop.create_task(self.dj(playlist, channel, updates))

    async def stop(self):
        if not self.playing:
            return

        self._vc.stop()
        await self._vc.disconnect()
        self.playing = False

    def skip(self):
        if not self.playing:
            return

        self._skip = True
