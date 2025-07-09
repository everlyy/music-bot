import dataclasses

@dataclasses.dataclass
class Playlist:
    name: str
    source: str
    tracks: list[str]
