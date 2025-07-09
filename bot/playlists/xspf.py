from .common import Playlist
from bs4 import BeautifulSoup
import os
import pathlib
import urllib.parse

def parse(path: str) -> Playlist:
    name = pathlib.Path(path).stem
    tracks: list[str] = []

    file = open(path, "rb")
    data = file.read()
    file.close()

    bs = BeautifulSoup(data, "xml")
    for tag in bs.find_all("location"):
        tracks.append(urllib.parse.unquote(tag.text))

    return Playlist(name, path, tracks)

def find_and_parse(folder: str) -> list[Playlist]:
    playlists: list[Playlist] = []

    for file in os.listdir(folder):
        path = os.path.join(folder, file)
        if not os.path.isfile(path):
            continue

        if not path.endswith(".xspf"):
            continue

        playlists.append(parse(path))

    return playlists
