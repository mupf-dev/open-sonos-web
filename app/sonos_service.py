"""Steuerung echter Sonos-Lautsprecher über SoCo (lokale UPnP-API, ohne Cloud)."""

from __future__ import annotations

import datetime as dt
import ipaddress
import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

import soco
from soco import SoCo, alarms
from soco.data_structures import DidlObject, to_didl_string
from soco.data_structures_entry import from_didl_string
from soco.discovery import scan_network
from soco.exceptions import SoCoUPnPException

from .music_services import ServiceHub

log = logging.getLogger("sonos")

CONFIG_PATH = Path(os.environ.get("SONOS_CONFIG", Path(__file__).resolve().parent.parent / "data" / "config.json"))

# URI-Präfixe, die als Stream (nicht über die Warteschlange) abgespielt werden
STREAM_PREFIXES = (
    "x-sonosapi-stream:", "x-sonosapi-radio:", "x-rincon-mp3radio:", "x-sonosapi-hls:",
    "x-sonosapi-hls-static:", "aac:", "hls-radio:", "x-rincon-stream:", "x-sonos-htastream:",
)
CONTAINER_PREFIXES = ("x-rincon-cpcontainer:", "x-rincon-playlist:", "file:///jffs/settings/savedqueues")

RECURRENCES = ("DAILY", "WEEKDAYS", "WEEKENDS", "ONCE")
PLAY_MODES = {
    (False, "off"): "NORMAL", (False, "all"): "REPEAT_ALL", (False, "one"): "REPEAT_ONE",
    (True, "off"): "SHUFFLE_NOREPEAT", (True, "all"): "SHUFFLE", (True, "one"): "SHUFFLE_REPEAT_ONE",
}

# Einstellungen, die je nach Modell vorhanden sind (None = nicht unterstützt)
EQ_INT = {"bass": (-10, 10), "treble": (-10, 10), "balance": (-100, 100), "sub_gain": (-15, 15),
          "surround_level": (-15, 15), "music_surround_level": (-15, 15), "audio_delay": (0, 5)}
EQ_BOOL = ("loudness", "night_mode", "dialog_mode", "sub_enabled", "surround_enabled",
           "surround_full_volume_enabled", "trueplay")


class NotConnected(Exception):
    pass


def _time_to_sec(value: str | None) -> int:
    if not value or value.startswith("NOT_IMPLEMENTED"):
        return 0
    try:
        h, m, s = value.split(":")
        return int(h) * 3600 + int(m) * 60 + int(float(s))
    except ValueError:
        return 0


def _sec_to_time(sec: int) -> str:
    sec = max(0, int(sec))
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


class SonosService:
    demo = False

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._zones: dict[str, SoCo] = {}
        self._zones_at = 0.0
        self._known_ips: set[str] = set()
        self._pool = ThreadPoolExecutor(max_workers=16)
        self.config = self._load_config()
        self.hub = ServiceHub(CONFIG_PATH.parent / "music_tokens.json")
        self._covers: dict[str, tuple[float, list[str], int]] = {}
        self._cover_jobs: set[str] = set()

    # ------------------------------------------------------------------ Konfiguration / Discovery
    def _load_config(self) -> dict:
        try:
            return json.loads(CONFIG_PATH.read_text())
        except (OSError, ValueError):
            return {"hosts": []}

    def _save_config(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(self.config, indent=2))

    def _seed_hosts(self) -> list[str]:
        env = [h.strip() for h in os.environ.get("SONOS_HOSTS", "").split(",") if h.strip()]
        return env + [h for h in self.config.get("hosts", []) if h not in env]

    def _refresh_zones(self, force: bool = False) -> dict[str, SoCo]:
        with self._lock:
            if not force and time.time() - self._zones_at < (30 if self._zones else 10):
                return self._zones
            zones: set[SoCo] = set()
            for host in self._seed_hosts() + list(self._known_ips):
                try:
                    zones = SoCo(host).visible_zones or set()
                    if zones:
                        break
                except Exception as exc:  # noqa: BLE001 - Host nicht erreichbar
                    log.debug("Seed %s nicht erreichbar: %s", host, exc)
            if not zones:
                try:
                    zones = soco.discover(timeout=3) or set()
                except Exception as exc:  # noqa: BLE001
                    log.debug("Discovery fehlgeschlagen: %s", exc)
            self._zones = {z.uid: z for z in zones}
            if zones:
                self.hub.device = next(iter(zones))
            self._known_ips = {z.ip_address for z in zones}
            self._zones_at = time.time()
            return self._zones

    def system(self) -> dict:
        zones = self._refresh_zones()
        return {"demo": False, "connected": bool(zones), "hosts": self._seed_hosts(),
                "speakers": len(zones)}

    def add_host(self, host: str) -> dict:
        try:
            ipaddress.ip_address(host)
        except ValueError:
            raise ValueError("Bitte eine gültige IP-Adresse eingeben") from None
        info = SoCo(host).get_speaker_info(refresh=True, timeout=4)
        hosts = self.config.setdefault("hosts", [])
        if host not in hosts:
            hosts.insert(0, host)
            self._save_config()
        self._refresh_zones(force=True)
        return {"ok": True, "name": info.get("zone_name")}

    def remove_host(self, host: str) -> dict:
        self.config["hosts"] = [h for h in self.config.get("hosts", []) if h != host]
        self._save_config()
        return {"ok": True}

    def prefs(self) -> dict:
        """Oberflächen-Einstellungen, die auf allen Geräten gelten (z. B. Reihenfolge der Zeilen)."""
        return self.config.get("prefs", {})

    def set_prefs(self, data: dict) -> dict:
        self.config.setdefault("prefs", {}).update(data)
        self._save_config()
        return self.config["prefs"]

    def scan(self, network: str | None) -> dict:
        nets = [str(ipaddress.ip_network(network, strict=False))] if network else None
        found = scan_network(networks_to_scan=nets, max_threads=256, scan_timeout=0.4,
                             min_netmask=16) or set()
        if found:
            ip = next(iter(found)).ip_address
            hosts = self.config.setdefault("hosts", [])
            if ip not in hosts:
                hosts.insert(0, ip)
                self._save_config()
        self._refresh_zones(force=True)
        return {"found": sorted(z.ip_address for z in found)}

    def _dev(self, uid: str) -> SoCo:
        zones = self._refresh_zones()
        if not zones:
            raise NotConnected("Kein Sonos-System erreichbar")
        dev = zones.get(uid) or self._refresh_zones(force=True).get(uid)
        if dev is None:
            raise KeyError(f"Lautsprecher {uid} unbekannt")
        return dev

    def _coord(self, uid: str) -> SoCo:
        dev = self._dev(uid)
        return dev.group.coordinator if dev.group else dev

    # ------------------------------------------------------------------ Hilfen
    def art_url(self, url: str | None) -> str | None:
        if not url:
            return None
        host = urlparse(url).hostname
        if host in self._known_ips:
            return "/api/art?u=" + quote(url, safe="")
        return url if url.startswith(("http://", "https://")) else None

    def is_speaker_url(self, url: str) -> bool:
        p = urlparse(url)
        return p.scheme == "http" and p.hostname in self._known_ips and p.port == 1400

    def _item(self, obj, dev: SoCo | None = None) -> dict:
        cls = getattr(obj, "item_class", "") or ""
        art = getattr(obj, "album_art_uri", None)
        if art and dev is not None and not art.startswith("http"):
            art = dev.music_library.build_album_art_full_uri(art)
        res = getattr(obj, "resources", None) or []
        return {
            "id": obj.item_id,
            "title": obj.title,
            "subtitle": getattr(obj, "creator", None) or getattr(obj, "album", None)
            or getattr(obj, "description", None) or "",
            "album": getattr(obj, "album", None),
            "kind": cls.split(".")[-1],
            "container": cls.startswith("object.container"),
            "playable": bool(res),
            "art": self.art_url(art),
        }

    def _browse_raw(self, dev: SoCo, object_id: str, flag: str, start=0, count=100):
        res = dev.contentDirectory.Browse([
            ("ObjectID", object_id), ("BrowseFlag", flag), ("Filter", "*"),
            ("StartingIndex", start), ("RequestedCount", count), ("SortCriteria", ""),
        ])
        return from_didl_string(res["Result"]), int(res.get("TotalMatches", 0))

    # ------------------------------------------------------------------ Status
    def state(self) -> dict:
        zones = self._refresh_zones()
        if not zones:
            return {"connected": False, "groups": []}
        any_dev = next(iter(zones.values()))
        groups = [g for g in any_dev.all_groups if g.coordinator and g.coordinator.is_visible]
        result = list(self._pool.map(self._group_state, groups))
        result.sort(key=lambda g: g["name"].lower())
        return {"connected": True, "groups": result}

    def _group_state(self, group) -> dict:
        c = group.coordinator
        members = sorted((m for m in group.members if m.is_visible), key=lambda m: m.player_name.lower())
        try:
            transport = c.get_current_transport_info()["current_transport_state"]
            track = c.get_current_track_info()
            media = c.get_current_media_info()
            play_mode = c.play_mode
            source = c.music_source_from_uri(track.get("uri") or media.get("uri") or "")
            sleep = c.get_sleep_timer()
            mstate = [self._member_state(m) for m in members]
            gvol = round(sum(m["volume"] for m in mstate) / len(mstate)) if mstate else 0
            title = track.get("title") or ""
            artist = track.get("artist") or ""
            if source in ("TV", "LINE_IN"):
                # Sonos liefert hier nur die Geräte-ID als „Sender“
                owner = next((m["name"] for m in mstate if m["uid"] in (track.get("uri") or "")), c.player_name)
                title = "Fernseher" if source == "TV" else "Line-In"
                artist = owner
            elif source in ("RADIO", "WEB_FILE") or media.get("channel"):
                station = media.get("channel") or title
                if title.startswith(("x-sonosapi", "x-rincon")) or title == station:
                    title = station
                    station = ""
                artist = artist or station
            return {
                "uid": c.uid, "name": self._group_name(c, mstate),
                "coordinator": c.uid, "state": transport,
                "track": {
                    "title": title, "artist": artist, "album": track.get("album") or "",
                    "art": self.art_url(track.get("album_art")),
                    "position": _time_to_sec(track.get("position")),
                    "duration": _time_to_sec(track.get("duration")),
                    "queue_position": int(track.get("playlist_position") or 0),
                },
                "source": source,
                "shuffle": "SHUFFLE" in play_mode,
                "repeat": "one" if "REPEAT_ONE" in play_mode else ("all" if play_mode in ("REPEAT_ALL", "SHUFFLE") else "off"),
                "crossfade": bool(c.cross_fade),
                "sleep": sleep,
                "volume": gvol,
                "mute": all(m["mute"] for m in mstate) if mstate else False,
                "members": mstate,
            }
        except Exception as exc:  # noqa: BLE001 - Gruppe gerade nicht erreichbar
            log.warning("Status für %s fehlgeschlagen: %s", c.player_name, exc)
            return {"uid": c.uid, "name": c.player_name, "coordinator": c.uid, "state": "ERROR",
                    "error": str(exc), "members": [], "track": {}, "volume": 0, "mute": False}

    @staticmethod
    def _group_name(c: SoCo, mstate: list[dict]) -> str:
        """Wie in der Sonos-App: führender Raum zuerst."""
        names = [m["name"] for m in mstate if m["uid"] == c.uid] + [m["name"] for m in mstate if m["uid"] != c.uid]
        if not names:
            return c.player_name
        return " + ".join(names) if len(names) <= 2 else f"{names[0]} + {len(names) - 1}"

    def _member_state(self, m: SoCo) -> dict:
        return {"uid": m.uid, "name": m.player_name, "volume": m.volume, "mute": m.mute,
                "fixed_volume": bool(getattr(m, "fixed_volume", False))}

    def speaker_list(self) -> list[dict]:
        zones = self._refresh_zones()
        out = []
        for z in zones.values():
            info = z.get_speaker_info()
            out.append({"uid": z.uid, "name": z.player_name, "model": info.get("model_name"),
                        "ip": z.ip_address, "coordinator": z.group.coordinator.uid if z.group else z.uid})
        return sorted(out, key=lambda s: s["name"].lower())

    # ------------------------------------------------------------------ Wiedergabe
    def transport(self, uid: str, action: str) -> None:
        c = self._coord(uid)
        {"play": c.play, "pause": c.pause, "stop": c.stop, "next": c.next, "previous": c.previous}[action]()

    def seek(self, uid: str, position: int) -> None:
        self._coord(uid).seek(_sec_to_time(position))

    def set_play_mode(self, uid: str, shuffle: bool, repeat: str) -> None:
        self._coord(uid).play_mode = PLAY_MODES[(bool(shuffle), repeat)]

    def set_crossfade(self, uid: str, enabled: bool) -> None:
        self._coord(uid).cross_fade = bool(enabled)

    def set_sleep(self, uid: str, minutes: int | None) -> None:
        self._coord(uid).set_sleep_timer(int(minutes) * 60 if minutes else None)

    def set_volume(self, uid: str, volume: int | None = None, mute: bool | None = None,
                   relative: int | None = None) -> None:
        dev = self._dev(uid)
        if volume is not None:
            dev.volume = max(0, min(100, int(volume)))
        if relative is not None:
            dev.set_relative_volume(int(relative))
        if mute is not None:
            dev.mute = bool(mute)

    def set_group_volume(self, uid: str, volume: int | None = None, mute: bool | None = None) -> None:
        group = self._coord(uid).group
        members = [m for m in group.members if m.is_visible]
        if volume is not None:
            target = max(0, min(100, int(volume)))
            try:
                group.volume = target
            except SoCoUPnPException:
                # manche Gruppen (z. B. mit Soundbar im TV-Betrieb) lehnen die Gruppenlautstärke ab (801):
                # dann alle Räume um denselben Betrag verschieben, wie es die Sonos-App tut
                current = [m.volume for m in members]
                delta = target - round(sum(current) / len(current))
                for m, v in zip(members, current):
                    if not getattr(m, "fixed_volume", False):
                        m.volume = max(0, min(100, v + delta))
        if mute is not None:
            try:
                group.mute = bool(mute)
            except SoCoUPnPException:
                for m in members:
                    m.mute = bool(mute)

    def switch_source(self, uid: str, source: str) -> None:
        dev = self._dev(uid)
        if source == "tv":
            dev.switch_to_tv()
        else:
            dev.switch_to_line_in()
        dev.play()

    # ------------------------------------------------------------------ Gruppen
    def join(self, uid: str, target: str) -> None:
        self._dev(uid).join(self._coord(target))
        self._zones_at = 0

    def unjoin(self, uid: str) -> None:
        self._dev(uid).unjoin()
        self._zones_at = 0

    def set_group(self, coordinator: str, members: list[str]) -> None:
        """Gruppe auf genau diese Mitglieder setzen."""
        c = self._dev(coordinator)
        if c.group.coordinator.uid != c.uid:
            c.unjoin()
            time.sleep(0.3)
        wanted = set(members) | {coordinator}
        for uid, dev in self._refresh_zones().items():
            in_group = dev.group and dev.group.coordinator.uid == c.uid
            if uid in wanted and not in_group:
                dev.join(c)
            elif uid not in wanted and in_group and uid != coordinator:
                dev.unjoin()
        self._zones_at = 0

    def party(self, uid: str) -> None:
        self._dev(uid).partymode()
        self._zones_at = 0

    def ungroup_all(self) -> None:
        for dev in self._refresh_zones().values():
            if dev.group and len([m for m in dev.group.members if m.is_visible]) > 1 and not dev.is_coordinator:
                dev.unjoin()
        self._zones_at = 0

    # ------------------------------------------------------------------ Warteschlange
    def queue(self, uid: str, start: int, count: int) -> dict:
        c = self._coord(uid)
        q = c.get_queue(start=start, max_items=count, full_album_art_uri=True)
        items = []
        for i, t in enumerate(q):
            d = self._item(t, c)
            d.update(index=start + i, subtitle=" · ".join(x for x in (getattr(t, "creator", ""), getattr(t, "album", "")) if x))
            items.append(d)
        return {"items": items, "total": q.total_matches}

    def queue_action(self, uid: str, action: str, index: int | None = None, to: int | None = None,
                     title: str | None = None) -> None:
        c = self._coord(uid)
        if action == "play":
            c.play_from_queue(int(index))
        elif action == "remove":
            c.remove_from_queue(int(index))
        elif action == "move":
            c.move_in_queue(int(index), int(to))
        elif action == "clear":
            c.clear_queue()
        elif action == "save":
            c.create_sonos_playlist_from_queue(title or "Neue Playlist")
        else:
            raise ValueError(action)

    # ------------------------------------------------------------------ Favoriten / Playlists / Bibliothek
    def favorites(self, uid: str) -> list[dict]:
        dev = self._dev(uid)
        favs = dev.music_library.get_sonos_favorites(full_album_art_uri=True)
        out = []
        for f in favs:
            d = self._item(f, dev)
            ref = getattr(f, "reference", None)
            uri = f.resources[0].uri if f.resources else ""
            d["stream"] = uri.startswith(STREAM_PREFIXES) or "audioBroadcast" in getattr(ref, "item_class", "")
            d["subtitle"] = getattr(f, "description", None) or ""
            # Ordner-Favoriten von Streamingdiensten (z. B. „Deine Bibliothek“ bei Spotify) haben keine
            # abspielbare Adresse – sie lassen sich nur über die Dienst-Anmeldung der Sonos-App öffnen
            d["playable"] = bool(uri)
            if not uri:
                d["browse_id"] = self.hub.favorite_target(f)
            out.append(d)
        return out

    def _play_favorite(self, c: SoCo, fav_id: str, mode: str) -> None:
        fav = next((f for f in c.music_library.get_sonos_favorites() if f.item_id == fav_id), None)
        if fav is None:
            raise KeyError("Favorit nicht gefunden")
        if not fav.resources:
            raise ValueError(f"„{fav.title}“ ist ein Ordner bei einem Streamingdienst und lässt sich "
                             "nur in der Sonos-App öffnen")
        uri = fav.resources[0].uri
        meta = fav.resource_meta_data
        ref_class = getattr(getattr(fav, "reference", None), "item_class", "") or ""
        if uri.startswith(STREAM_PREFIXES) or "audioBroadcast" in ref_class:
            c.play_uri(uri, meta)
            return
        self._enqueue_uri(c, uri, meta, mode)

    def _enqueue_uri(self, c: SoCo, uri: str, meta: str, mode: str) -> None:
        if mode == "replace":
            c.clear_queue()
        position = 0
        if mode == "next":
            pos = int(c.get_current_track_info().get("playlist_position") or 0)
            position = pos + 1 if pos else 0
        res = c.avTransport.AddURIToQueue([
            ("InstanceID", 0), ("EnqueuedURI", uri), ("EnqueuedURIMetaData", meta),
            ("DesiredFirstTrackNumberEnqueued", position), ("EnqueueAsNext", int(mode == "next")),
        ])
        if mode in ("replace", "now"):
            first = int(res.get("FirstTrackNumberEnqueued", 1))
            c.play_from_queue(max(0, first - 1))

    def play_item(self, uid: str, item_id: str, mode: str = "replace", title: str = "") -> None:
        """Bibliotheks-/Playlist-/Favoriteneintrag abspielen oder einreihen.

        mode: replace (Warteschlange ersetzen), now (einfügen & abspielen), next, add
        """
        c = self._coord(uid)
        if item_id.startswith("svc:"):
            uri, didl, stream = self.hub.playable(c, item_id, title)
            if stream:
                c.play_uri(uri, didl)
            else:
                self._enqueue_uri(c, uri, didl, mode)
            return
        if item_id.startswith("FV:"):
            return self._play_favorite(c, item_id, mode)
        items, _ = self._browse_raw(c, item_id, "BrowseMetadata", 0, 1)
        if not items:
            raise KeyError("Eintrag nicht gefunden")
        item: DidlObject = items[0]
        if not item.resources:
            raise ValueError("Dieser Eintrag ist nicht abspielbar")
        uri = item.resources[0].uri
        if uri.startswith(STREAM_PREFIXES) or "audioBroadcast" in item.item_class:
            c.play_uri(uri, to_didl_string(item))
            return
        self._enqueue_uri(c, uri, to_didl_string(item), mode)

    def browse(self, uid: str, object_id: str, start: int, count: int, search: str | None = None) -> dict:
        dev = self._dev(uid)
        if object_id.startswith("svc:"):
            return self.hub.browse(dev, object_id, start, count, search)
        if search:
            object_id = f"{object_id}:{quote(search)}"
        items, total = self._browse_raw(dev, object_id, "BrowseDirectChildren", start, count)
        return {"items": [self._item(i, dev) for i in items], "total": total}

    # ------------------------------------------------------------------ Musikdienste
    def services(self, uid: str) -> list[dict]:
        """Dienste, die im System genutzt werden (laut Favoriten) oder hier verbunden sind."""
        dev = self._dev(uid)
        household = dev.household_id
        cat = self.hub.catalog()
        used = set()
        for f in dev.music_library.get_sonos_favorites():
            uri = f.resources[0].uri if f.resources else ""
            if "sid=" in uri:
                used.add(uri.split("sid=", 1)[1].split("&", 1)[0])
            elif target := self.hub.favorite_target(f):
                used.add(target.split(":")[1])
        used |= {sid for sid in cat if cat[sid]["auth"] != "Anonymous" and self.hub.is_linked(sid, household)}
        out = [{"sid": sid, "name": cat[sid]["name"], "auth": cat[sid]["auth"],
                "linked": self.hub.is_linked(sid, household),
                "root": f"svc:{sid}:container:root"} for sid in used if sid in cat]
        return sorted(out, key=lambda s: (not s["linked"], s["name"].lower()))

    def service_link(self, uid: str, sid: str, step: str) -> dict:
        dev = self._dev(uid)
        if step == "begin":
            return {"url": self.hub.link_begin(sid, dev)}
        if step == "complete":
            self.hub.link_complete(sid)
            return {"ok": True}
        if step == "unlink":
            self.hub.unlink(sid, dev.household_id)
            return {"ok": True}
        raise ValueError(step)

    def playlists(self, uid: str) -> list[dict]:
        dev = self._dev(uid)
        items = [self._item(p, dev) for p in dev.get_sonos_playlists()]
        for item in items:
            hit = self._covers.get(item["id"])
            if hit and time.time() - hit[0] < 600:
                item.update(arts=hit[1], art=hit[1][0] if hit[1] else None, subtitle=f"{hit[2]} Titel")
            else:
                # Cover im Hintergrund suchen (erste Suche dauert), das Frontend lädt nach
                item["covers_pending"] = True
                if item["id"] not in self._cover_jobs:
                    self._cover_jobs.add(item["id"])
                    self._pool.submit(self._cover_job, dev, item["id"])
        return items

    def _cover_job(self, dev: SoCo, playlist_id: str) -> None:
        try:
            self._playlist_cover(dev, playlist_id)
        finally:
            self._cover_jobs.discard(playlist_id)

    def _art_works(self, track, art: str | None) -> bool:
        """Cover vom Lautsprecher sind bei Titeln nicht mehr verfügbarer Dienste leer (0 Byte)."""
        if not art:
            return False
        if not art.startswith("/api/art"):
            return True
        uri = track.resources[0].uri if track.resources else ""
        if "sid=" not in uri:
            return True  # lokale Datei / NAS
        sid = uri.split("sid=", 1)[1].split("&", 1)[0]
        return sid in self.hub.catalog() and self.hub.is_linked(sid, self.hub.device.household_id) \
            if self.hub.device else True

    def _playlist_cover(self, dev: SoCo, playlist_id: str) -> tuple[list[str], int]:
        """Bis zu vier verschiedene Cover der ersten Titel (für das Mosaik) + Titelanzahl, 10 Min. zwischengespeichert."""
        hit = self._covers.get(playlist_id)
        if hit and time.time() - hit[0] < 600:
            return hit[1], hit[2]
        try:
            tracks, total = self._browse_raw(dev, playlist_id, "BrowseDirectChildren", 0, 30)
        except Exception:  # noqa: BLE001 - Cover sind nur Deko
            self._covers[playlist_id] = (time.time(), [], 0)
            return [], 0
        arts: list[str] = []
        for t in tracks:
            art = self._item(t, dev)["art"]
            if not self._art_works(t, art):
                artist, album = getattr(t, "creator", "") or "", getattr(t, "album", "") or ""
                uri = t.resources[0].uri if t.resources else ""
                if not (artist or album) and uri.startswith("x-file-cifs:"):
                    # Dateien ohne Tags: …/Interpret/Album/Titel.flac
                    parts = unquote(uri).split("/")
                    artist, album = (parts[-3], parts[-2]) if len(parts) >= 4 else ("", "")
                art = self.hub.cover_for(dev, artist, album)
            if art and art not in arts:
                arts.append(art)
            if len(arts) == 4:
                break
        self._covers[playlist_id] = (time.time(), arts, total)
        return arts, total

    def delete_playlist(self, uid: str, playlist_id: str) -> None:
        self._covers.pop(playlist_id, None)
        dev = self._dev(uid)
        pl = next((p for p in dev.get_sonos_playlists() if p.item_id == playlist_id), None)
        if pl is None:
            raise KeyError("Playlist nicht gefunden")
        dev.remove_sonos_playlist(pl)

    def rename_playlist(self, uid: str, playlist_id: str, title: str) -> None:
        self._covers.pop(playlist_id, None)
        dev = self._dev(uid)
        pl = next((p for p in dev.get_sonos_playlists() if p.item_id == playlist_id), None)
        if pl is None:
            raise KeyError("Playlist nicht gefunden")
        dev.contentDirectory.UpdateObject([
            ("ObjectID", playlist_id),
            ("CurrentTagValue", f"<dc:title>{pl.title}</dc:title>"),
            ("NewTagValue", f"<dc:title>{title}</dc:title>"),
        ])

    def add_to_playlist(self, uid: str, playlist_id: str, item_id: str) -> None:
        self._covers.pop(playlist_id, None)
        dev = self._dev(uid)
        pl = next((p for p in dev.get_sonos_playlists() if p.item_id == playlist_id), None)
        items, _ = self._browse_raw(dev, item_id, "BrowseMetadata", 0, 1)
        if pl is None or not items:
            raise KeyError("Playlist oder Eintrag nicht gefunden")
        dev.add_item_to_sonos_playlist(items[0], pl)

    def library_update(self, uid: str) -> None:
        self._dev(uid).music_library.start_library_update()

    # ------------------------------------------------------------------ Klang & Einstellungen
    def settings(self, uid: str) -> dict:
        dev = self._dev(uid)
        info = dev.get_speaker_info()
        eq: dict = {}
        for key in list(EQ_INT) + list(EQ_BOOL):
            try:
                val = getattr(dev, key)
                if key == "balance":  # SoCo liefert (links, rechts) 0–100 → -100 (links) … +100 (rechts)
                    val = val[1] - val[0]
            except Exception:  # noqa: BLE001 - vom Modell nicht unterstützt
                val = None
            if val is not None:
                eq[key] = int(val) if key in EQ_INT else bool(val)
        battery = None
        if "Move" in (info.get("model_name") or "") or "Roam" in (info.get("model_name") or ""):
            try:
                battery = dev.get_battery_info(timeout=2)
            except Exception:  # noqa: BLE001
                battery = None
        return {
            "uid": dev.uid, "name": dev.player_name, "model": info.get("model_name"),
            "model_number": info.get("model_number"), "version": info.get("display_version") or info.get("software_version"),
            "ip": dev.ip_address, "mac": info.get("mac_address"), "serial": info.get("serial_number"),
            "status_light": bool(dev.status_light), "buttons_enabled": self._safe(lambda: dev.buttons_enabled),
            "is_soundbar": bool(self._safe(lambda: dev.is_soundbar)),
            "line_in": self._has_line_in(info.get("model_name") or ""),
            "eq": eq, "ranges": {k: v for k, v in EQ_INT.items() if k in eq}, "battery": battery,
        }

    @staticmethod
    def _safe(fn):
        try:
            return fn()
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _has_line_in(model: str) -> bool:
        return any(k in model for k in ("Five", "Play:5", "Port", "Connect", "Amp", "Era 100", "Era 300", "Move", "Roam 2"))

    def update_settings(self, uid: str, data: dict) -> None:
        dev = self._dev(uid)
        for key, val in data.items():
            if key == "balance":
                b = max(-100, min(100, int(val)))
                dev.balance = (100 - b, 100) if b >= 0 else (100, 100 + b)
            elif key in EQ_INT:
                lo, hi = EQ_INT[key]
                setattr(dev, key, max(lo, min(hi, int(val))))
            elif key in EQ_BOOL or key in ("status_light", "buttons_enabled"):
                setattr(dev, key, bool(val))
            elif key == "name" and str(val).strip():
                dev.player_name = str(val).strip()[:40]
                self._zones_at = 0
            else:
                raise ValueError(f"Unbekannte Einstellung: {key}")

    # ------------------------------------------------------------------ Wecker
    def alarms(self) -> list[dict]:
        zones = self._refresh_zones()
        if not zones:
            raise NotConnected("Kein Sonos-System erreichbar")
        out = []
        for a in alarms.get_alarms(next(iter(zones.values()))):
            if a.zone is None:
                continue
            out.append({
                "id": a.alarm_id, "uid": a.zone.uid, "room": a.zone.player_name,
                "time": a.start_time.strftime("%H:%M"),
                "duration": int(a.duration.hour * 60 + a.duration.minute) if a.duration else None,
                "recurrence": a.recurrence, "enabled": a.enabled, "volume": a.volume,
                "play_mode": a.play_mode, "include_linked": a.include_linked_zones,
                "program": self._alarm_program_title(a),
                "program_uri": a.program_uri,
            })
        return sorted(out, key=lambda x: x["time"])

    @staticmethod
    def _alarm_program_title(a) -> str:
        if not a.program_uri or a.program_uri == "x-rincon-buzzer:0":
            return "Sonos-Klingelton"
        try:
            items = from_didl_string(a.program_metadata)
            return items[0].title if items else "Musik"
        except Exception:  # noqa: BLE001
            return "Musik"

    def save_alarm(self, data: dict, alarm_id: str | None = None) -> None:
        dev = self._dev(data["uid"])
        if alarm_id:
            a = next((x for x in alarms.get_alarms(dev) if x.alarm_id == alarm_id), None)
            if a is None:
                raise KeyError("Wecker nicht gefunden")
            a.zone = dev
        else:
            a = alarms.Alarm(dev)
        h, m = (int(x) for x in data["time"].split(":"))
        a.start_time = dt.time(h, m)
        dur = int(data.get("duration") or 0)
        a.duration = dt.time(dur // 60, dur % 60) if dur else None
        rec = data.get("recurrence", "DAILY")
        if rec not in RECURRENCES and not (rec.startswith("ON_") and rec[3:].isdigit()):
            raise ValueError("Ungültige Wiederholung")
        a.recurrence = rec
        a.enabled = bool(data.get("enabled", True))
        a.volume = max(0, min(100, int(data.get("volume", 20))))
        a.include_linked_zones = bool(data.get("include_linked", False))
        a.play_mode = data.get("play_mode", "NORMAL")
        program = data.get("program_id")
        if program == "keep" and alarm_id:
            pass
        elif program and program != "buzzer":
            fav = next((f for f in dev.music_library.get_sonos_favorites() if f.item_id == program), None)
            if fav is None:
                raise KeyError("Favorit nicht gefunden")
            a.program_uri = fav.resources[0].uri
            a.program_metadata = fav.resource_meta_data
        else:
            a.program_uri = None
            a.program_metadata = ""
        a.save()

    def delete_alarm(self, alarm_id: str) -> None:
        zones = self._refresh_zones()
        if not zones:
            raise NotConnected("Kein Sonos-System erreichbar")
        alarms.remove_alarm_by_id(next(iter(zones.values())), alarm_id)
