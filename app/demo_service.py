"""Simuliertes Sonos-System, um die Oberfläche ohne Lautsprecher auszuprobieren (SONOS_DEMO=1)."""

from __future__ import annotations

import copy
import itertools
import random
import time

ARTISTS = {
    "Nordlicht": [("Polarnacht", ["Aurora", "Eiskristall", "Weiter Horizont", "Stille See"]),
                  ("Morgengrau", ["Erstes Licht", "Nebelbank", "Hafenstadt"])],
    "The Quiet Rooms": [("Paper Walls", ["Open Window", "Static", "Late Train", "Hallway Light", "Home"])],
    "Miro Vale": [("Analog Summer", ["Sunburnt", "Cassette", "Pool Lights", "August"])],
}
COLORS = ["#d8d2c4", "#3b4252", "#c4a484", "#8fa3a3", "#b48ead", "#5e81ac"]


def _art(title: str) -> str:
    color = COLORS[sum(map(ord, title)) % len(COLORS)].replace("#", "%23")
    initial = title[:1].upper()
    return ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>"
            f"<rect width='100' height='100' fill='{color}'/><text x='50' y='62' font-family='sans-serif' "
            f"font-size='34' text-anchor='middle' fill='white' fill-opacity='.85'>{initial}</text></svg>")


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
            "RINCON_WOHN": {"name": "Wohnzimmer", "model": "Sonos Arc", "volume": 28, "mute": False, "soundbar": True},
            "RINCON_KUECHE": {"name": "Küche", "model": "Sonos Era 100", "volume": 22, "mute": False, "soundbar": False},
            "RINCON_BAD": {"name": "Bad", "model": "Sonos One SL", "volume": 18, "mute": False, "soundbar": False},
            "RINCON_BUERO": {"name": "Büro", "model": "Sonos Five", "volume": 30, "mute": False, "soundbar": False},
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
        self.players["RINCON_WOHN"].update(queue=self.tracks[:7], index=2, state="PLAYING", pos=41, source="LIBRARY")
        self.players["RINCON_BUERO"].update(queue=self.tracks[7:12], state="PAUSED_PLAYBACK", pos=95, source="LIBRARY")
        self.favs = [
            {"id": "FV:2/1", "title": "Radio Paradise", "subtitle": "Radiosender", "stream": True},
            {"id": "FV:2/2", "title": "Deutschlandfunk", "subtitle": "Radiosender", "stream": True},
            {"id": "FV:2/3", "title": "Polarnacht", "subtitle": "Nordlicht", "stream": False, "album": "Polarnacht"},
            {"id": "FV:2/4", "title": "Paper Walls", "subtitle": "The Quiet Rooms", "stream": False, "album": "Paper Walls"},
        ]
        self.playlists_ = {"SQ:1": {"title": "Sonntagmorgen", "tracks": self.tracks[3:9]},
                           "SQ:2": {"title": "Fokus", "tracks": self.tracks[12:]}}
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
            raise KeyError(f"Lautsprecher {uid} unbekannt")
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
                track = {"title": p["stream"], "artist": "Live-Radio", "album": "", "art": _art(p["stream"]),
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
                "name": " + ".join(m["name"] for m in members),
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
        raise KeyError("Eintrag nicht gefunden")

    def services(self, uid: str) -> list[dict]:
        return []

    def service_link(self, uid: str, sid: str, step: str) -> dict:
        raise ValueError("Im Demo-Modus nicht verfügbar")

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
        if object_id == "A:ALBUMARTIST" or object_id == "A:ARTIST":
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
        return [{"id": k, "title": v["title"], "subtitle": f"{len(v['tracks'])} Titel", "kind": "playlistContainer",
                 "container": True, "playable": True, "art": _art(v["title"])} for k, v in self.playlists_.items()]

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
                raise ValueError(f"Unbekannte Einstellung: {k}")

    # ------------------------------------------------------------------ Wecker
    def alarms(self) -> list[dict]:
        out = []
        for a in self.alarms_:
            fav = next((f for f in self.favs if f["id"] == a["program_id"]), None)
            out.append(a | {"room": self.speakers[a["uid"]]["name"],
                            "program": fav["title"] if fav else "Sonos-Klingelton"})
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
