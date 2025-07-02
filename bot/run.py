from config import *
import lastfm
import music_bot
import commands


if __name__ == "__main__":
    bot = music_bot.MusicBot(
        PLAYLISTS_PATH,
        lastfm.LastFM(LASTFM_API_KEY, LASTFM_SECRET),
        lastfm.LastFMSessionManager(LASTFM_SESSIONS_FILE)
    )

    for group in commands.GROUPS:
        bot.tree.add_command(group)

    bot.run(DISCORD_TOKEN)
