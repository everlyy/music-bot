from commands.common import bot
from config import *
import discord

GROUP = discord.app_commands.Group(name="current", description="Currently playing music commands")

@GROUP.command(name="stop", description="Stop")
async def current_stop(interaction: discord.Interaction):
    await bot(interaction).stop()
    await interaction.response.send_message("Bye")

@GROUP.command(name="skip", description="Skip to the next track")
async def current_skip(interaction: discord.Interaction):
    bot(interaction).skip()
    await interaction.response.send_message("Skipped")

@GROUP.command(name="download", description="Send file of currently playing song")
async def current_download(interaction: discord.Interaction):
    track = bot(interaction).track

    if track is None:
        await interaction.response.send_message(f"Nothing has been played yet")
        return

    await interaction.response.defer()

    try:
        await interaction.followup.send(file=discord.File(track))
    except Exception as e:
        await interaction.followup.send(f"Couldn't send file: `{e}`")
