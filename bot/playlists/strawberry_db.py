from .common import Playlist
from urllib.parse import unquote, urlparse
import sqlite3

def parse(path: str) -> (list[Playlist] | None):
    c = sqlite3.connect(path)

    # Probably possible in a single query, I'm just not enough of a sql witch
    playlists: list[Playlist] = []
    for playlist_rowid, playlist_name in c.execute("SELECT ROWID, name FROM playlists"):
        tracks: list[str] = []

        query = "SELECT url FROM songs WHERE ROWID IN (SELECT collection_id FROM playlist_items WHERE playlist = ?)"
        args = (playlist_rowid, )
        for url, *_ in c.execute(query, args):
            path = unquote(urlparse(url).path)
            tracks.append(path)

        playlists.append(Playlist(playlist_name, "strawberry.db", tracks))

    c.close()

    return playlists
