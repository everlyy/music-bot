import os
from .common import Playlist

SUPPORTED_EXTENSIONS = [".mp3", ".m4a", ".flac", ".wav"]

def parse(path: str) -> Playlist:
    playlist = Playlist("All Music", path, [])

    for root, dirs, files in os.walk(path):
        for file in files:
            track_path = os.path.join(root, file)
            if os.path.splitext(file)[1] in SUPPORTED_EXTENSIONS:
                playlist.tracks.append(track_path)

    return playlist
