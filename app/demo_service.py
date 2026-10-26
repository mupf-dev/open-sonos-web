"""Simuliertes Sonos-System, um die Oberfläche ohne Lautsprecher auszuprobieren (SONOS_DEMO=1)."""

from __future__ import annotations

import copy
import itertools
import random
import time

from .errors import AppError

ARTISTS = {
    "Nordlicht": [("Polarnacht", ["Aurora", "Eiskristall", "Weiter Horizont", "Stille See"]),
                  ("Morgengrau", ["Erstes Licht", "Nebelbank", "Hafenstadt"])],
    "The Quiet Rooms": [("Paper Walls", ["Open Window", "Static", "Late Train", "Hallway Light", "Home"])],
    "Miro Vale": [("Analog Summer", ["Sunburnt", "Cassette", "Pool Lights", "August"])],
    "Lumen Drive": [("Neon Hours", ["Midnight Signal", "Chrome Hearts", "City Glow", "Afterimage"]),
                    ("Low Orbit", ["Satellite", "Gravity Well", "Re-Entry"])],
    "Saltwater Choir": [("Tidal", ["Undertow", "Harbour Lights", "Driftwood", "Low Tide"])],
    "Velvet Static": [("Slow Bloom", ["Honey", "Paper Moon", "Soft Focus", "Golden Hour"])],
}
# Farbpaare für die erzeugten Demo-Cover (abstrakte Verläufe, keine echten Cover)
PALETTES = [("#ff6b6b", "#5f27cd"), ("#0abde3", "#10ac84"), ("#feca57", "#ff6b6b"), ("#48dbfb", "#341f97"),
            ("#ff9ff3", "#5f27cd"), ("#1dd1a1", "#222f3e"), ("#c8d6e5", "#576574"), ("#ee5253", "#0a3d62"),
            ("#f6e58d", "#6ab04c"), ("#7ed6df", "#e056fd"), ("#fab1a0", "#2d3436"), ("#55efc4", "#0984e3")]
LYRICS = ["The city's still asleep, but I'm awake", "Streetlights drifting past the window", "We're quieter than the rain",
          "But still they hear us", "Hold the moment for a while", "Everything sounds like summer",
          "An echo in the empty streets", "We keep on walking towards the morning", "No plan, just this song",
          "And the bass carries us home", "Ooh, ooh", "Stay a little longer"]


def _art(seed: str) -> str:
    h = sum(ord(c) * (i + 1) for i, c in enumerate(seed))
    a, b = PALETTES[h % len(PALETTES)]
    cx, cy, r = 18 + h % 64, 18 + (h // 7) % 64, 22 + (h // 13) % 26
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><defs><linearGradient id='g' x1='0' y1='0' "
           f"x2='1' y2='1'><stop offset='0' stop-color='{a}'/><stop offset='1' stop-color='{b}'/></linearGradient></defs>"
           f"<rect width='100' height='100' fill='url(#g)'/><circle cx='{cx}' cy='{cy}' r='{r}' fill='white' "
           f"fill-opacity='.2'/><circle cx='{100 - cx}' cy='{100 - cy}' r='{r // 2}' fill='black' fill-opacity='.14'/>"
           f"<rect x='0' y='{(h // 3) % 80}' width='100' height='1.2' fill='white' fill-opacity='.35'/></svg>")
    return "data:image/svg+xml;utf8," + svg.replace("#", "%23")


class DemoService:
    demo = True

    def __init__(self) -> None:
        self.tracks = []
        for artist, albums in ARTISTS.items():
            for album, titles in albums:
                for t in titles:
                    self.tracks.append({"id": f"T:{len(self.tracks)}", "title": t, "artist": artist,
                                        "album": album, "duration": random.randint(150, 300)})
        self.speakers = {
            "RINCON_WOHN": {"name": "Living Room", "model": "Sonos Arc", "volume": 28, "mute": False, "soundbar": True},
            "RINCON_KUECHE": {"name": "Kitchen", "model": "Sonos Era 100", "volume": 22, "mute": False, "soundbar": False},
            "RINCON_BAD": {"name": "Bathroom", "model": "Sonos One SL", "volume": 18, "mute": False, "soundbar": False},
            "RINCON_BUERO": {"name": "Office", "model": "Sonos Five", "volume": 30, "mute": False, "soundbar": False},
        }
        for uid, s in self.speakers.items():
            s.update(uid=uid, status_light=True, buttons_enabled=True,
                     eq={"bass": 0, "treble": 0, "balance": 0, "loudness": True}
                     | ({"night_mode": False, "dialog_mode": False, "sub_enabled": True, "sub_gain": 0,
                         "surround_enabled": True, "surround_level": 0} if s["soundbar"] else {}))
        self.membership = {"RINCON_WOHN": "RINCON_WOHN", "RINCON_KUECHE": "RINCON_WOHN",
                           "RINCON_BAD": "RINCON_BAD", "RINCON_BUERO": "RINCON_BUERO"}
        self.players = {}
        for uid in self.speakers:
            self.players[uid] = {"queue": [], "index": 0, "state": "STOPPED", "pos": 0.0, "since": time.time(),
                                 "shuffle": False, "repeat": "off", "crossfade": False, "sleep_until": None,
                                 "stream": None, "source": "NONE"}
        self.players["RINCON_WOHN"].update(queue=self.tracks[16:31], index=0, state="PLAYING", pos=52, source="LIBRARY")
        self.players["RINCON_BUERO"].update(queue=self.tracks[7:12], state="PAUSED_PLAYBACK", pos=95, source="LIBRARY")
        self.favs = [
            {"id": "FV:2/1", "title": "Morning FM", "subtitle": "Radio", "stream": True},
            {"id": "FV:2/2", "title": "City Radio", "subtitle": "Radio", "stream": True},
            {"id": "FV:2/3", "title": "Polarnacht", "subtitle": "Nordlicht", "stream": False, "album": "Polarnacht"},
            {"id": "FV:2/4", "title": "Paper Walls", "subtitle": "The Quiet Rooms", "stream": False, "album": "Paper Walls"},
            {"id": "FV:2/5", "title": "Neon Hours", "subtitle": "Lumen Drive", "stream": False, "album": "Neon Hours"},
            {"id": "FV:2/6", "title": "Jazz Lounge FM", "subtitle": "Radio", "stream": True},
            {"id": "FV:2/7", "title": "Tidal", "subtitle": "Saltwater Choir", "stream": False, "album": "Tidal"},
            {"id": "FV:2/8", "title": "Slow Bloom", "subtitle": "Velvet Static", "stream": False, "album": "Slow Bloom"},
        ]
        self.playlists_ = {"SQ:1": {"title": "Sunday Morning", "tracks": self.tracks[3:16:2]},
                           "SQ:2": {"title": "Focus", "tracks": self.tracks[12:]},
                           "SQ:3": {"title": "Dinner", "tracks": self.tracks[1::3]},
                           "SQ:4": {"title": "Road Trip", "tracks": self.tracks[::4]},
                           "SQ:5": {"title": "Favourites", "tracks": self.tracks[2::5]},
                           "SQ:6": {"title": "Calm", "tracks": self.tracks[20:]}}
        self.alarms_ = [{"id": "1", "uid": "RINCON_BAD", "time": "06:45", "duration": 60, "recurrence": "WEEKDAYS",
                         "enabled": True, "volume": 15, "play_mode": "NORMAL", "include_linked": False,
                         "program_id": "FV:2/2"}]
        self._ids = itertools.count(10)

    # ------------------------------------------------------------------ System
    def system(self) -> dict:
        return {"demo": True, "connected": True, "hosts": [], "speakers": len(self.speakers)}

    def add_host(self, host: str) -> dict:
        return {"ok": True, "name": "Demo"}

    def remove_host(self, host: str) -> dict:
        return {"ok": True}

    def prefs(self) -> dict:
        return self.__dict__.setdefault("_prefs", {})

    def set_prefs(self, data: dict) -> dict:
        self.prefs().update(data)
        return self.prefs()

    def scan(self, network):
        return {"found": []}

    def art_url(self, url):
        return url

    def is_speaker_url(self, url):
        return False

    # ------------------------------------------------------------------ Hilfen
    def _coord(self, uid: str) -> str:
        if uid not in self.membership:
            raise AppError("speaker_unknown", 404)
        return self.membership[uid]

    def _members(self, coord: str) -> list[str]:
        return sorted((u for u, c in self.membership.items() if c == coord), key=lambda u: self.speakers[u]["name"])

    def _tick(self, p: dict) -> None:
        now = time.time()
        if p["sleep_until"] and now >= p["sleep_until"]:
            p.update(state="PAUSED_PLAYBACK", sleep_until=None)
        if p["state"] == "PLAYING" and p["queue"] and not p["stream"]:
            p["pos"] += now - p["since"]
            while p["pos"] >= p["queue"][p["index"]]["duration"]:
                p["pos"] -= p["queue"][p["index"]]["duration"]
                if p["repeat"] != "one":
                    p["index"] = (p["index"] + 1) % len(p["queue"])
        p["since"] = now

    def _track(self, t: dict) -> dict:
        return {"id": t["id"], "title": t["title"], "subtitle": f"{t['artist']} · {t['album']}", "album": t["album"],
                "kind": "musicTrack", "container": False, "playable": True, "art": _art(t["album"])}

    # ------------------------------------------------------------------ Status
    def state(self) -> dict:
        groups = []
        for coord in sorted(set(self.membership.values()), key=lambda u: self.speakers[u]["name"]):
            p = self.players[coord]
            self._tick(p)
            members = [{"uid": u, "name": self.speakers[u]["name"], "volume": self.speakers[u]["volume"],
                        "mute": self.speakers[u]["mute"], "fixed_volume": False} for u in self._members(coord)]
            if p["stream"]:
                track = {"title": p["stream"], "artist": "Live", "album": "", "art": _art(p["stream"]),
                         "position": int(time.time() - p["since"]), "duration": 0, "queue_position": 0}
            elif p["queue"]:
                t = p["queue"][p["index"]]
                track = {"title": t["title"], "artist": t["artist"], "album": t["album"], "art": _art(t["album"]),
                         "position": int(p["pos"]), "duration": t["duration"], "queue_position": p["index"] + 1}
            else:
                track = {"title": "", "artist": "", "album": "", "art": None, "position": 0, "duration": 0,
                         "queue_position": 0}
            groups.append({
                "uid": coord, "coordinator": coord,
                "name": " + ".join(m["name"] for m in sorted(members, key=lambda m: m["uid"] != coord)),
                "state": p["state"], "track": track, "source": p["source"],
                "shuffle": p["shuffle"], "repeat": p["repeat"], "crossfade": p["crossfade"],
                "sleep": int(p["sleep_until"] - time.time()) if p["sleep_until"] else None,
                "volume": round(sum(m["volume"] for m in members) / len(members)),
                "mute": all(m["mute"] for m in members), "members": members,
            })
        return {"connected": True, "groups": groups}

    def speaker_list(self) -> list[dict]:
        return [{"uid": u, "name": s["name"], "model": s["model"], "ip": "demo", "coordinator": self.membership[u]}
                for u, s in sorted(self.speakers.items(), key=lambda x: x[1]["name"])]

    # ------------------------------------------------------------------ Wiedergabe
    def transport(self, uid: str, action: str) -> None:
        p = self.players[self._coord(uid)]
        self._tick(p)
        if action == "play" and (p["queue"] or p["stream"]):
            p["state"] = "PLAYING"
        elif action in ("pause", "stop"):
            p["state"] = "PAUSED_PLAYBACK" if action == "pause" else "STOPPED"
        elif action in ("next", "previous") and p["queue"] and not p["stream"]:
            if action == "previous" and p["pos"] > 3:
                p["pos"] = 0
                return
            step = 1 if action == "next" else -1
            p["index"] = (random.randrange(len(p["queue"])) if p["shuffle"] and action == "next"
                          else (p["index"] + step) % len(p["queue"]))
            p["pos"] = 0

    def seek(self, uid: str, position: int) -> None:
        p = self.players[self._coord(uid)]
        self._tick(p)
        p["pos"] = float(position)

    def set_play_mode(self, uid: str, shuffle: bool, repeat: str) -> None:
        self.players[self._coord(uid)].update(shuffle=bool(shuffle), repeat=repeat)

    def set_crossfade(self, uid: str, enabled: bool) -> None:
        self.players[self._coord(uid)]["crossfade"] = bool(enabled)

    def set_sleep(self, uid: str, minutes) -> None:
        self.players[self._coord(uid)]["sleep_until"] = time.time() + int(minutes) * 60 if minutes else None

    def set_volume(self, uid, volume=None, mute=None, relative=None) -> None:
        s = self.speakers[uid]
        if volume is not None:
            s["volume"] = max(0, min(100, int(volume)))
        if relative is not None:
            s["volume"] = max(0, min(100, s["volume"] + int(relative)))
        if mute is not None:
            s["mute"] = bool(mute)

    def set_group_volume(self, uid, volume=None, mute=None) -> None:
        members = self._members(self._coord(uid))
        if volume is not None:
            current = sum(self.speakers[m]["volume"] for m in members) / len(members)
            delta = int(volume) - current
            for m in members:
                self.speakers[m]["volume"] = max(0, min(100, round(self.speakers[m]["volume"] + delta)))
        if mute is not None:
            for m in members:
                self.speakers[m]["mute"] = bool(mute)

    def switch_source(self, uid: str, source: str) -> None:
        p = self.players[self._coord(uid)]
        p.update(stream="TV" if source == "tv" else "Line-In", state="PLAYING", source=source.upper().replace("LINEIN", "LINE_IN"))

    # ------------------------------------------------------------------ Gruppen
    def join(self, uid: str, target: str) -> None:
        coord = self._coord(target)
        self.unjoin(uid)
        self.membership[uid] = coord

    def unjoin(self, uid: str) -> None:
        old = self.membership[uid]
        if old == uid:
            rest = [m for m in self._members(uid) if m != uid]
            if rest:
                new = rest[0]
                self.players[new] = copy.deepcopy(self.players[uid])
                for m in rest:
                    self.membership[m] = new
        self.membership[uid] = uid
        self.players[uid].update(state="STOPPED")

    def set_group(self, coordinator: str, members: list[str]) -> None:
        if self.membership[coordinator] != coordinator:
            self.unjoin(coordinator)
        wanted = set(members) | {coordinator}
        for uid in list(self.membership):
            if uid in wanted and self.membership[uid] != coordinator:
                self.join(uid, coordinator)
            elif uid not in wanted and self.membership[uid] == coordinator and uid != coordinator:
                self.unjoin(uid)

    def party(self, uid: str) -> None:
        coord = self._coord(uid)
        for u in self.membership:
            self.membership[u] = coord

    def ungroup_all(self) -> None:
        for u in list(self.membership):
            if self.membership[u] != u:
                self.unjoin(u)

    # ------------------------------------------------------------------ Warteschlange
    def queue(self, uid: str, start: int, count: int) -> dict:
        q = self.players[self._coord(uid)]["queue"]
        items = []
        for i, t in enumerate(q[start:start + count]):
            d = self._track(t)
            d["index"] = start + i
            items.append(d)
        return {"items": items, "total": len(q)}

    def queue_action(self, uid, action, index=None, to=None, title=None) -> None:
        p = self.players[self._coord(uid)]
        q = p["queue"]
        if action == "play":
            p.update(index=int(index), pos=0, state="PLAYING", stream=None, since=time.time(), source="LIBRARY")
        elif action == "remove":
            q.pop(int(index))
            if int(index) < p["index"] or p["index"] >= len(q):
                p["index"] = max(0, p["index"] - 1)
            if not q:
                p.update(state="STOPPED", index=0, pos=0)
        elif action == "move":
            current = q[p["index"]] if q else None
            q.insert(int(to), q.pop(int(index)))
            if current is not None:
                p["index"] = q.index(current)
        elif action == "clear":
            p.update(queue=[], index=0, pos=0, state="STOPPED" if not p["stream"] else p["state"])
        elif action == "save":
            self.playlists_[f"SQ:{next(self._ids)}"] = {"title": title or "Neue Playlist", "tracks": list(q)}

    # ------------------------------------------------------------------ Inhalte
    def favorites(self, uid: str) -> list[dict]:
        return [{"id": f["id"], "title": f["title"], "subtitle": f["subtitle"], "kind": "favorite",
                 "container": not f["stream"], "playable": True, "stream": f["stream"], "art": _art(f["title"])}
                for f in self.favs]

    def _tracks_for(self, item_id: str) -> list[dict]:
        if item_id.startswith("svc:demo:"):
            name = item_id.split(":", 3)[3]
            album = [t for t in self.tracks if t["album"] == name]
            if album:
                return album
            h = sum(map(ord, name))
            return [self.tracks[(h + i * 5) % len(self.tracks)] for i in range(8)]
        if item_id.startswith("FV:"):
            fav = next(f for f in self.favs if f["id"] == item_id)
            return [t for t in self.tracks if t["album"] == fav.get("album")]
        if item_id.startswith("SQ:"):
            return list(self.playlists_[item_id]["tracks"])
        if item_id.startswith("T:"):
            return [t for t in self.tracks if t["id"] == item_id]
        kind, _, name = item_id.partition("/")
        if kind == "A:ALBUM":
            return [t for t in self.tracks if t["album"] == name]
        if kind in ("A:ALBUMARTIST", "A:ARTIST"):
            return [t for t in self.tracks if t["artist"] == name]
        if item_id == "A:TRACKS":
            return list(self.tracks)
        raise AppError("item_not_found", 404)

    # ------------------------------------------------------------------ Demo-Musikdienst
    SECTIONS = {"forYou": ("Made for you", "playlist"), "new": ("New releases", "album"),
                "moods": ("Moods", "playlist"), "yours": ("Your music", "playlist")}
    MOODS = ["Focus", "Sunday Morning", "Running", "Dinner", "Road Trip", "Rainy Day", "Party", "Sleep"]

    def services(self, uid: str) -> list[dict]:
        return [{"sid": "demo", "name": "Streaming", "auth": "AppLink", "linked": True,
                 "root": "svc:demo:container:root"}]

    def _svc_item(self, kind: str, name: str, subtitle: str = "") -> dict:
        return {"id": f"svc:demo:{kind}:{name}", "title": name, "subtitle": subtitle,
                "kind": "musicAlbum" if kind == "album" else "playlistContainer",
                "container": True, "playable": True, "art": _art(name)}

    def _svc_browse(self, object_id: str) -> list[dict]:
        _, _, kind, name = object_id.split(":", 3)
        if name == "root":
            return [{"id": f"svc:demo:section:{k}", "title": t, "subtitle": "", "kind": "container",
                     "container": True, "playable": False, "art": None} for k, (t, _) in self.SECTIONS.items()]
        if kind == "section":
            if name == "forYou":
                return [self._svc_item("playlist", n, "Made for you") for n in
                        ("Weekly Mix", "New for You", "Daily Mix 1", "Daily Mix 2", "Time Capsule", "Liked Songs", "Discoveries")]
            if name == "new":
                return [self._svc_item("album", al, a) for a, albums in ARTISTS.items() for al, _ in albums]
            if name == "moods":
                return [self._svc_item("playlist", n, "Mood") for n in self.MOODS]
            return [self._svc_item("playlist", n, "Playlist") for n in ("Liked Songs", "Car", "Cooking", "Workout")]
        return [self._track(t) for t in self._tracks_for(object_id)]

    def service_link(self, uid: str, sid: str, step: str) -> dict:
        raise AppError("demo_unavailable")

    def play_item(self, uid: str, item_id: str, mode: str = "replace", title: str = "") -> None:
        p = self.players[self._coord(uid)]
        fav = next((f for f in self.favs if f["id"] == item_id), None)
        if fav and fav["stream"]:
            p.update(stream=fav["title"], state="PLAYING", since=time.time(), source="RADIO")
            return
        tracks = self._tracks_for(item_id)
        if mode == "replace" or not p["queue"]:
            p.update(queue=tracks, index=0, pos=0, state="PLAYING", stream=None, since=time.time(), source="LIBRARY")
        elif mode in ("next", "now"):
            at = p["index"] + 1
            p["queue"][at:at] = tracks
            if mode == "now":
                p.update(index=at, pos=0, state="PLAYING", stream=None)
        else:
            p["queue"].extend(tracks)

    def browse(self, uid, object_id, start, count, search=None) -> dict:
        items: list[dict] = []
        if object_id.startswith("svc:demo:"):
            items = self._svc_browse(object_id) if not search else [
                self._track(t) for t in self.tracks if search.lower() in (t["title"] + t["artist"]).lower()]
            search = None
        elif object_id == "A:ALBUMARTIST" or object_id == "A:ARTIST":
            items = [{"id": f"A:ALBUMARTIST/{a}", "title": a, "subtitle": "", "kind": "musicArtist",
                      "container": True, "playable": True, "art": _art(a)} for a in ARTISTS]
        elif object_id == "A:ALBUM":
            items = [{"id": f"A:ALBUM/{al}", "title": al, "subtitle": a, "kind": "musicAlbum", "container": True,
                      "playable": True, "art": _art(al)} for a, albums in ARTISTS.items() for al, _ in albums]
        elif object_id == "A:TRACKS":
            items = [self._track(t) for t in self.tracks]
        elif object_id.startswith("A:ALBUMARTIST/"):
            artist = object_id.split("/", 1)[1]
            items = [{"id": f"A:ALBUM/{al}", "title": al, "subtitle": artist, "kind": "musicAlbum", "container": True,
                      "playable": True, "art": _art(al)} for al, _ in ARTISTS.get(artist, [])]
        elif object_id.startswith(("A:ALBUM/", "SQ:")):
            items = [self._track(t) for t in self._tracks_for(object_id)]
        elif object_id in ("A:GENRE", "A:COMPOSER", "A:PLAYLISTS", "S:"):
            items = []
        if search:
            items = [i for i in items if search.lower() in (i["title"] + i["subtitle"]).lower()]
        return {"items": items[start:start + count], "total": len(items)}

    def playlists(self, uid: str) -> list[dict]:
        out = []
        for k, v in self.playlists_.items():
            arts = list(dict.fromkeys(_art(t["album"]) for t in v["tracks"]))[:4]
            out.append({"id": k, "title": v["title"], "subtitle": "", "count": len(v["tracks"]), "kind": "playlistContainer",
                        "container": True, "playable": True, "art": arts[0] if arts else None, "arts": arts})
        return out

    # ------------------------------------------------------------------ Demo-Medien (Songtext, Interpret)
    def lyrics(self, artist: str, title: str, duration: int = 0) -> dict | None:
        t = next((x for x in self.tracks if x["title"] == title and x["artist"] == artist), None)
        if not t:
            return None
        h = sum(map(ord, title))
        lines = [f"[{s // 60:02d}:{s % 60:02d}.00]{LYRICS[(h + i) % len(LYRICS)]}"
                 for i, s in enumerate(range(6, t["duration"], 5))]
        return {"synced": "\n".join(lines), "plain": None, "instrumental": False, "source": "Demo"}

    def artist_info(self, name: str) -> dict | None:
        if name not in ARTISTS:
            return None
        albums = ", ".join(al for al, _ in ARTISTS[name])
        return {"name": name, "description": "Fictional act from demo mode", "image": _art(name + " artist"),
                "extract": f"{name} doesn't really exist – this act shows how the stage view presents artist info. "
                           f"With real speakers, photo and text come from Wikipedia. Albums: {albums}.",
                "url": None, "source": "Demo"}

    def delete_playlist(self, uid, playlist_id) -> None:
        self.playlists_.pop(playlist_id)

    def rename_playlist(self, uid, playlist_id, title) -> None:
        self.playlists_[playlist_id]["title"] = title

    def add_to_playlist(self, uid, playlist_id, item_id) -> None:
        self.playlists_[playlist_id]["tracks"].extend(self._tracks_for(item_id))

    def library_update(self, uid) -> None:
        pass

    # ------------------------------------------------------------------ Einstellungen
    def settings(self, uid: str) -> dict:
        s = self.speakers[uid]
        ranges = {"bass": (-10, 10), "treble": (-10, 10), "balance": (-100, 100), "sub_gain": (-15, 15),
                  "surround_level": (-15, 15)}
        return {"uid": uid, "name": s["name"], "model": s["model"], "model_number": "DEMO", "version": "16.4",
                "ip": "192.168.0.x", "mac": "00:00:00:00:00:00", "serial": "demo",
                "status_light": s["status_light"], "buttons_enabled": s["buttons_enabled"],
                "is_soundbar": s["soundbar"], "line_in": s["model"].endswith(("Five", "Era 100")),
                "eq": dict(s["eq"]), "ranges": {k: v for k, v in ranges.items() if k in s["eq"]}, "battery": None}

    def update_settings(self, uid: str, data: dict) -> None:
        s = self.speakers[uid]
        for k, v in data.items():
            if k == "name":
                s["name"] = str(v).strip()[:40] or s["name"]
            elif k in ("status_light", "buttons_enabled"):
                s[k] = bool(v)
            elif k in s["eq"]:
                s["eq"][k] = v if isinstance(v, bool) else int(v)
            else:
                raise AppError("unknown_setting", key=k)

    # ------------------------------------------------------------------ Wecker
    def alarms(self) -> list[dict]:
        out = []
        for a in self.alarms_:
            fav = next((f for f in self.favs if f["id"] == a["program_id"]), None)
            out.append(a | {"room": self.speakers[a["uid"]]["name"],
                            "program": fav["title"] if fav else ""})
        return sorted(out, key=lambda x: x["time"])

    def save_alarm(self, data: dict, alarm_id=None) -> None:
        if alarm_id:
            a = next(x for x in self.alarms_ if x["id"] == alarm_id)
        else:
            a = {"id": str(next(self._ids)), "program_id": "buzzer"}
            self.alarms_.append(a)
        a.update({k: data[k] for k in ("uid", "time", "duration", "recurrence", "enabled", "volume",
                                        "play_mode", "include_linked") if k in data})
        if data.get("program_id") and data["program_id"] != "keep":
            a["program_id"] = data["program_id"]

    def delete_alarm(self, alarm_id: str) -> None:
        self.alarms_ = [a for a in self.alarms_ if a["id"] != alarm_id]
