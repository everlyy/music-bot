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
import typing
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
                print(f"  {item.name}:")
                for cmd in item.walk_commands():
                    assert isinstance(cmd, discord.app_commands.Command)
                    print(f"    - {cmd.name}")
            else:
                if item.parent is not None:
                    continue
                print(f"  - {item.name}")

        print(f"Have {len(self.playlists)} playlist(s)")
        for playlist in self.playlists:
            print(f"  - {playlist.name} ({len(playlist.tracks)} track(s))")

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

lastfm_group = discord.app_commands.Group(name="lastfm", description="LastFM related commands")
bot = MusicBot(
    PLAYLISTS_PATH,
    lastfm.LastFM(LASTFM_API_KEY, LASTFM_SECRET),
    lastfm.LastFMSessionManager(LASTFM_SESSIONS_FILE)
)
bot.tree.add_command(lastfm_group)

@bot.tree.command(name="reload", description=f"Reload all playlists")
async def reload(interaction: discord.Interaction):
    await interaction.response.send_message(f"Reloading playlists...")
    bot.reload_playlists()
    await interaction.edit_original_response(content=f"Reloaded playlists")

@bot.tree.command(name="playlists", description="List available playlists")
async def playlists(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Playlists",
        description=f"Have {len(bot.playlists)} playlist(s)"
    )

    for playlist in bot.playlists:
        embed.add_field(
            name=playlist.name,
            value=f"-# {playlist.path}\n{len(playlist.tracks)} track(s)",
            inline=False
        )

    await interaction.response.send_message(embed=embed)

async def autocomplete_playlist(_: discord.Interaction, current: str) -> list[discord.app_commands.Choice[str]]:
    playlist_names = [playlist.name for playlist in bot.playlists]
    return [
        discord.app_commands.Choice(name=playlist_name, value=playlist_name)
        for playlist_name in playlist_names if current.lower() in playlist_name.lower()
    ]

@bot.tree.command(name="play", description="Play a playlist")
@discord.app_commands.autocomplete(playlist_name=autocomplete_playlist)
@discord.app_commands.rename(playlist_name="playlist")
@discord.app_commands.guild_only()
async def play(interaction: discord.Interaction, playlist_name: str):
    assert interaction.guild is not None
    assert isinstance(interaction.user, discord.Member)
    assert isinstance(interaction.channel, discord.TextChannel)

    if interaction.user.voice is None:
        await interaction.response.send_message("You must be in a voice channel to begin playing music")
        return

    assert isinstance(interaction.user.voice.channel, discord.VoiceChannel)

    playlist = bot.find_playlist_by_name(playlist_name)
    if playlist is None:
        await interaction.response.send_message(f"Couldn't find playlist with name `{playlist_name}`")
        return

    await typing.cast(MusicBot, interaction.client).play(playlist, interaction.user.voice.channel, interaction.channel)
    await interaction.guild.change_voice_state(channel=interaction.user.voice.channel, self_deaf=True, self_mute=False)
    await interaction.response.send_message("Hi")

@bot.tree.command(name="stop", description="Stop")
async def stop(interaction: discord.Interaction):
    await typing.cast(MusicBot, interaction.client).stop()
    await interaction.response.send_message("Bye")

@bot.tree.command(name="skip", description="Skip to the next track")
async def skip(interaction: discord.Interaction):
    typing.cast(MusicBot, interaction.client).skip()
    await interaction.response.send_message("Skipped")

@lastfm_group.command(name="link", description="Link your last.fm account to the bot for scrobbling")
async def lastfm_link(interaction: discord.Interaction):
    await interaction.response.send_message("Generating URL, please wait", ephemeral=True)

    token = await bot.lfm.auth_get_token()
    auth_url = bot.lfm.get_auth_url(token)

    await interaction.edit_original_response(content=f"Please open [this link](<{auth_url}>) in your browser to authenticate")

    await asyncio.sleep(3)

    session: (tuple[str, str] | None) = None

    for _ in range(10):
        try:
            session = await bot.lfm.auth_get_session(token)
        except:
            await asyncio.sleep(1)

    if session is None:
        await interaction.edit_original_response(content=f"You didn't authenticate in time")
        return

    name, key = session
    bot.lfmsm.add_session(str(interaction.user.id), key)
    await interaction.edit_original_response(content=f"Successfully authenticated as {name}")

@lastfm_group.command(name="unlink", description="Unlink your last.fm account from the bot")
async def lastfm_unlink(interaction: discord.Interaction):
    bot.lfmsm.remove_session(str(interaction.user.id))

bot.run(DISCORD_TOKEN)
