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
