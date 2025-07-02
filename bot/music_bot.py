from bs4 import BeautifulSoup
from config import *
import asyncio
import dataclasses
import discord
import lastfm
import os
import pathlib
import random
import time
import tinytag
import urllib.parse

@dataclasses.dataclass
class Metadata:
    title: (str | None)
    artist: (str | None)
    album: (str | None)
    album_artist: (str | None)

@dataclasses.dataclass
class Playlist:
    name: str
    path: str
    tracks: list[str]

class MusicBot(discord.Client):
    def __init__(self, playlists_path: str, lfm: lastfm.LastFM, lfmsm: lastfm.LastFMSessionManager):
        super().__init__(intents=discord.Intents.default())
        self.tree = discord.app_commands.CommandTree(self)
        self.playing: bool = False
        self.lfm = lfm
        self.lfmsm = lfmsm

        self._vc: discord.VoiceClient
        self._skip: bool = False
        self.playlists: list[Playlist] = []
        self._playlists_path = playlists_path
        self._scrobble_queue: list[tuple[str, Metadata]] = []

    async def scrobbler(self):
        while True:
            while len(self._scrobble_queue) > 0:
                user_id, metadata = self._scrobble_queue.pop()
                session_key = self.lfmsm.get_session(user_id)
                if session_key is None:
                    print(f"Couldn't find last.fm session key for {user_id}")
                    continue

                if metadata.artist is None or metadata.title is None:
                    print(f"Not scrobbling for {user_id} because there's not artist or title field")
                    continue

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
            await asyncio.sleep(5)

    async def on_ready(self):
        print(f"Syncing command tree")
        await self.tree.sync()

        print(f"Reloading playlist")
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

    def _parse_xspf_playlist(self, playlist: str) -> Playlist:
        name = pathlib.Path(playlist).stem
        path = os.path.abspath(playlist)
        tracks: list[str] = []

        file = open(playlist, "rb")
        data = file.read()
        file.close()

        bs = BeautifulSoup(data, "xml")
        for tag in bs.find_all("location"):
            tracks.append(urllib.parse.unquote(tag.text))

        return Playlist(name, path, tracks)

    def find_playlist_by_name(self, playlist_name: str) -> (Playlist | None):
        for playlist in self.playlists:
            if playlist.name == playlist_name:
                return playlist

        return None

    def reload_playlists(self) -> None:
        self.playlists.clear()

        for entry in os.listdir(self._playlists_path):
            path = os.path.join(self._playlists_path, entry)

            if not os.path.isfile(path):
                continue

            if path.lower().endswith(".xspf"):
                playlist = self._parse_xspf_playlist(path)
                self.playlists.append(playlist)

        return

    def get_metadata(self, track: str) -> (Metadata | None):
        tag = tinytag.TinyTag.get(track)
        metadata = Metadata(tag.title, tag.artist, tag.album, tag.albumartist)
        return metadata

    async def dj(self, playlist: Playlist, channel: discord.VoiceChannel, updates: discord.TextChannel):
        while self.playing:
            track = random.choice(playlist.tracks)
            self._vc.play(discord.FFmpegOpusAudio(track, bitrate=256))

            metadata = self.get_metadata(track)

            if metadata is not None:
                await updates.send(f"Now playing {metadata.title} by {metadata.artist}")
                for member in channel.members:
                    if member.id != self.application_id:
                        self._scrobble_queue.append((str(member.id), metadata))
            else:
                await updates.send(f"Now playing `{track}`\n-# This track will not scrobble because it does not have any metadata")

            while self._vc.is_playing():
                if self._skip:
                    self._vc.stop()
                    self._skip = False
                    break
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
