from commands.common import bot
from config import *
import discord

GROUP = discord.app_commands.Group(name="playlists", description="Playlist related commands")

@GROUP.command(name="reload", description=f"Reload all playlists")
async def playlists_reload(interaction: discord.Interaction):
    await interaction.response.send_message(f"Reloading playlists...")
    bot(interaction).reload_playlists()
    await interaction.edit_original_response(content=f"Reloaded playlists")

@GROUP.command(name="list", description="List available playlists")
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

@GROUP.command(name="play", description="Play a playlist")
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
