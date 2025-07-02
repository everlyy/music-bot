from config import *
import asyncio
import discord
import typing
import music_bot

def bot(interaction: discord.Interaction) -> music_bot.MusicBot:
    return typing.cast(music_bot.MusicBot, interaction.client)

playlists_group = discord.app_commands.Group(name="playlists", description="Playlist related commands")
current_group = discord.app_commands.Group(name="current", description="Currently playing music commands")
lastfm_group = discord.app_commands.Group(name="lastfm", description="LastFM related commands")

GROUPS = [ playlists_group, current_group, lastfm_group ]

@playlists_group.command(name="reload", description=f"Reload all playlists")
async def playlists_reload(interaction: discord.Interaction):
    await interaction.response.send_message(f"Reloading playlists...")
    bot(interaction).reload_playlists()
    await interaction.edit_original_response(content=f"Reloaded playlists")

@playlists_group.command(name="list", description="List available playlists")
async def playlists_list(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Playlists",
        description=f"Have {len(bot(interaction).playlists)} playlist(s)"
    )

    for playlist in bot(interaction).playlists:
        embed.add_field(
            name=playlist.name,
            value=f"-# {playlist.path}\n{len(playlist.tracks)} track(s)",
            inline=False
        )

    await interaction.response.send_message(embed=embed)

async def autocomplete_playlist(interaction: discord.Interaction, current: str) -> list[discord.app_commands.Choice[str]]:
    playlist_names = [playlist.name for playlist in bot(interaction).playlists]
    return [
        discord.app_commands.Choice(name=playlist_name, value=playlist_name)
        for playlist_name in playlist_names if current.lower() in playlist_name.lower()
    ]

@playlists_group.command(name="play", description="Play a playlist")
@discord.app_commands.autocomplete(playlist_name=autocomplete_playlist)
@discord.app_commands.rename(playlist_name="playlist")
@discord.app_commands.guild_only()
async def playlists_play(interaction: discord.Interaction, playlist_name: str):
    assert interaction.guild is not None
    assert isinstance(interaction.user, discord.Member)
    assert isinstance(interaction.channel, discord.TextChannel)

    if interaction.user.voice is None:
        await interaction.response.send_message("You must be in a voice channel to begin playing music")
        return

    assert isinstance(interaction.user.voice.channel, discord.VoiceChannel)

    playlist = bot(interaction).find_playlist_by_name(playlist_name)
    if playlist is None:
        await interaction.response.send_message(f"Couldn't find playlist with name `{playlist_name}`")
        return

    await bot(interaction).play(playlist, interaction.user.voice.channel, interaction.channel)
    await interaction.guild.change_voice_state(channel=interaction.user.voice.channel, self_deaf=True, self_mute=False)
    await interaction.response.send_message("Hi")

@current_group.command(name="stop", description="Stop")
async def current_stop(interaction: discord.Interaction):
    await bot(interaction).stop()
    await interaction.response.send_message("Bye")

@current_group.command(name="skip", description="Skip to the next track")
async def current_skip(interaction: discord.Interaction):
    bot(interaction).skip()
    await interaction.response.send_message("Skipped")

@lastfm_group.command(name="link", description="Link your last.fm account to the bot for scrobbling")
async def lastfm_link(interaction: discord.Interaction):
    await interaction.response.send_message("Generating URL, please wait", ephemeral=True)

    token = await bot(interaction).lfm.auth_get_token()
    auth_url = bot(interaction).lfm.get_auth_url(token)

    await interaction.edit_original_response(content=f"Please open [this link](<{auth_url}>) in your browser to authenticate")

    await asyncio.sleep(3)

    session: (tuple[str, str] | None) = None

    for _ in range(10):
        try:
            session = await bot(interaction).lfm.auth_get_session(token)
        except:
            await asyncio.sleep(1)

    if session is None:
        await interaction.edit_original_response(content=f"You didn't authenticate in time")
        return

    name, key = session
    bot(interaction).lfmsm.add_session(str(interaction.user.id), key)
    await interaction.edit_original_response(content=f"Successfully authenticated as {name}")

@lastfm_group.command(name="unlink", description="Unlink your last.fm account from the bot")
async def lastfm_unlink(interaction: discord.Interaction):
    bot(interaction).lfmsm.remove_session(str(interaction.user.id))
    await interaction.response.send_message(f"Your last.fm account was disconnected")
