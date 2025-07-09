from . import xspf, strawberry_db, collection
from .common import Playlist
import dataclasses
import os

STRAWBERRY_DB_PATH_DEFAULT = os.path.expanduser("~/.local/share/strawberry/strawberry/strawberry.db")

@dataclasses.dataclass
class SearchPaths:
    strawberry_db: str = STRAWBERRY_DB_PATH_DEFAULT
    xspf_path: (str | None) = None
    collection_path: (str | None) = None

def parse_all_playlists(paths: SearchPaths) -> list[Playlist]:
    playlists: list[Playlist] = []

    if os.path.exists(paths.strawberry_db):
        playlists.extend(strawberry_db.parse(paths.strawberry_db))

    if paths.xspf_path is not None:
        playlists.extend(xspf.find_and_parse(paths.xspf_path))

    if paths.collection_path is not None:
        playlists.append(collection.parse(paths.collection_path))

    return playlists
