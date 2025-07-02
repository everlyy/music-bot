from commands.common import bot
from config import *
import asyncio
import discord

GROUP = discord.app_commands.Group(name="lastfm", description="LastFM related commands")

@GROUP.command(name="link", description="Link your last.fm account to the bot for scrobbling")
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

@GROUP.command(name="unlink", description="Unlink your last.fm account from the bot")
async def lastfm_unlink(interaction: discord.Interaction):
    bot(interaction).lfmsm.remove_session(str(interaction.user.id))
    await interaction.response.send_message(f"Your last.fm account was disconnected")
