import datetime
from typing import Any
import aiohttp
import hashlib
import urllib.parse
import os
import json
import dataclasses

@dataclasses.dataclass
class LastFMUserInfo:
    name: str
    playcount: int
    artist_count: int
    track_count: int
    album_count: int
    image: str
    registered: datetime.datetime
    url: str

class LastFMSessionManager:
    def __init__(self, sessions_file: str):
        self.sessions_file = sessions_file
        self._sessions: dict[str, tuple[str, str]] = {}

        self._read()
        print(f"Loaded {len(self._sessions)} last.fm sessions from {self.sessions_file}")

    def _read(self) -> None:
        if not os.path.exists(self.sessions_file):
            return

        with open(self.sessions_file, "rb") as file:
            self._sessions = json.load(file)


    def _write(self) -> None:
        with open(self.sessions_file, "w") as file:
            json.dump(self._sessions, file, default=lambda o: o.__dict__)

    def add_session(self, user_id: str, session: tuple[str, str]) -> None:
        self._sessions[user_id] = session
        self._write()

    def get_session(self, user_id: str) -> (tuple[str, str] | None):
        if user_id not in self._sessions:
            return None
        return self._sessions[user_id]

    def remove_session(self, user_id: str) -> None:
        if user_id not in self._sessions:
            return

        del self._sessions[user_id]

class LastFM:
    API_ROOT: str = "http://ws.audioscrobbler.com/2.0/"

    def __init__(self, api_key: str, secret: str):
        self.api_key = api_key
        self.secret = secret
        self._session: aiohttp.ClientSession

    def _get_largest_image(self, image: list[dict[str, str]]) -> str:
        return image[len(image) - 1]["#text"]

    def _sign(self, params: dict[str, Any]):
        keys = list(params.keys())
        keys.sort()

        params_full: str = "".join([ f"{key}{params[key]}" for key in keys if key != "format" ])
        params_full += self.secret

        hasher = hashlib.md5()
        hasher.update(params_full.encode("utf-8"))
        return hasher.hexdigest()

    async def _get(self, method: str, sign: bool = False, params: dict[str, Any] = {}) -> Any:
        params |= {
            "method": method,
            "api_key": self.api_key,
            "format": "json"
        }

        if sign:
            params["api_sig"] = self._sign(params)

        async with self._session.get("", params=params) as response:
            response.raise_for_status()
            json = await response.json()
            return json

    async def _post(self, method: str, sign: bool = False, data: dict[str, Any] = {}) -> Any:
        data |= {
            "method": method,
            "api_key": self.api_key,
            "format": "json"
        }

        if sign:
            data["api_sig"] = self._sign(data)

        async with self._session.post("", data=data) as response:
            response.raise_for_status()
            json = await response.json()
            return json

    def init_session(self):
        self._session = aiohttp.ClientSession(base_url=LastFM.API_ROOT)

    async def auth_get_token(self) -> str:
        response = await self._get("auth.getToken", sign=True)
        return response["token"]

    def get_auth_url(self, token: str) -> str:
        return "http://www.last.fm/api/auth/?" + urllib.parse.urlencode({
            "api_key": self.api_key,
            "token": token
        })

    async def auth_get_session(self, token: str) -> tuple[str, str]:
        response = await self._get("auth.getSession", sign=True, params={
            "token": token
        })
        session = response["session"]
        return (session["name"], session["key"])

    async def track_scrobble(self, track: str, artist: str, album: (str | None), album_artist: (str | None), timestamp: int, session_key: str):
        return await self._post("track.scrobble", sign=True, data={
            "track": track,
            "artist": artist,
            "album": album,
            "albumArtist": album_artist,
            "timestamp": timestamp,
            "sk": session_key
        })

    async def track_update_now_playing(self, track: str, artist: str, album: (str | None), album_artist: (str | None), session_key: str):
        return await self._post("track.updateNowPlaying", sign=True, data={
            "track": track,
            "artist": artist,
            "album": album,
            "albumArtist": album_artist,
            "sk": session_key
        })

    async def user_get_info(self, user: str) -> LastFMUserInfo:
        response = await self._get("user.getinfo", params={
            "user": user
        })

        info = response["user"]

        return LastFMUserInfo(
            info["name"],
            int(info["playcount"]),
            int(info["artist_count"]),
            int(info["track_count"]),
            int(info["album_count"]),
            self._get_largest_image(info["image"]),
            datetime.datetime.fromtimestamp(int(info["registered"]["unixtime"])),
            info["url"]
        )
