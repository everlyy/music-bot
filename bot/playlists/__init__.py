import dataclasses
from . import xspf, strawberry_db
from .common import Playlist

@dataclasses.dataclass
class SearchPaths:
    strawberry_db: (str | None) = None
    xspf_path:     (str | None) = None

def parse_all_playlists(paths: SearchPaths) -> list[Playlist]:
    playlists: list[Playlist] = []

    playlists.extend(strawberry_db.parse(paths.strawberry_db))

    if paths.xspf_path is not None:
        playlists.extend(xspf.find_and_parse(paths.xspf_path))

    return playlists
