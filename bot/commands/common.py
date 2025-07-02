import discord
import music_bot
import typing

def bot(interaction: discord.Interaction) -> music_bot.MusicBot:
    return typing.cast(music_bot.MusicBot, interaction.client)
