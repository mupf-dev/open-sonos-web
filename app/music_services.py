"""Streamingdienste (Spotify, TuneIn, …) über die Sonos-Musikdienst-Schnittstelle (SMAPI).

Die Lautsprecher geben ihre Dienst-Anmeldung nicht heraus. Diese App verknüpft sich deshalb einmalig
selbst mit dem Dienst (AppLink/DeviceLink, wie ein weiteres Sonos-Steuergerät) und speichert das Token
in data/music_tokens.json. Abgespielt wird über Adressen, die die Lautsprecher mit ihrer eigenen
Anmeldung auflösen.

Einträge werden im Frontend als ``svc:<sid>:<typ>:<smapi-id>`` adressiert.
"""

from __future__ import annotations

import json
import os
import threading
from html import escape
from pathlib import Path
from urllib.parse import quote, unquote

from soco import SoCo
from soco.music_services import MusicService
from soco.music_services.music_service import parse_response
from soco.music_services.token_store import JsonFileTokenStore

# Typ → (DIDL-Präfix, UPnP-Klasse). Präfixe wie in den Favoriten der Sonos-App.
CONTAINER_TYPES = {
    "album": ("1004206c", "object.container.album.musicAlbum"),
    "playlist": ("1006206c", "object.container.playlistContainer"),
    "trackList": ("1006206c", "object.container.playlistContainer"),
    "albumList": ("1006206c", "object.container.playlistContainer"),
}
TRACK = ("10032020", "object.item.audioItem.musicTrack")
STREAM = ("F00092020", "object.item.audioItem.audioBroadcast")
DIDL = ('<DIDL-Lite xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/" '
        'xmlns:r="urn:schemas-rinconnetworks-com:metadata-1-0/" xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/">'
        '<item id="{id}" parentID="-1" restricted="true"><dc:title>{title}</dc:title><upnp:class>{cls}</upnp:class>'
        '<desc id="cdudn" nameSpace="urn:schemas-rinconnetworks-com:metadata-1-0/">{desc}</desc></item></DIDL-Lite>')


def make_id(sid: str, item_type: str, smapi_id: str) -> str:
    return f"svc:{sid}:{item_type}:{smapi_id}"


def split_id(item_id: str) -> tuple[str, str, str]:
    _, sid, item_type, smapi_id = item_id.split(":", 3)
    return sid, item_type, smapi_id


class ServiceHub:
    def __init__(self, token_path: Path) -> None:
        self.token_path = token_path
        self._lock = threading.Lock()
        self._services: dict[str, MusicService] = {}
        self._pending: dict[str, MusicService] = {}
        self._search_lock = threading.Lock()
        self._catalog: dict[str, dict] | None = None
        self.device: SoCo | None = None  # wird beim Erkennen der Lautsprecher gesetzt
        # SoCo lädt den Dienstkatalog sonst über die automatische Erkennung, die nicht überall klappt
        original = MusicService._get_music_services_data_xml
        MusicService._get_music_services_data_xml = staticmethod(lambda soco=None: original(soco or self.device))

    # ---------------------------------------------------------------- Katalog & Anmeldung
    def catalog(self) -> dict[str, dict]:
        """Alle Sonos-Musikdienste, nach Dienst-ID (sid)."""
        if self._catalog is None:
            cat = {}
            for name in MusicService.get_all_music_services_names():
                data = MusicService.get_data_for_name(name)
                cat[data["Id"]] = {"sid": data["Id"], "name": name, "auth": data["Auth"],
                                   "type": data["ServiceType"]}
            self._catalog = cat
        return self._catalog

    def sid_for_type(self, service_type: str) -> str | None:
        return next((s for s, d in self.catalog().items() if d["type"] == service_type), None)

    def _store(self) -> JsonFileTokenStore:
        return JsonFileTokenStore(str(self.token_path))

    def is_linked(self, sid: str, household: str) -> bool:
        info = self.catalog().get(sid)
        if not info:
            return False
        if info["auth"] == "Anonymous":
            return True
        return self._store().has_token(sid, household)

    def service(self, sid: str, dev: SoCo) -> MusicService:
        info = self.catalog().get(sid)
        if not info:
            raise KeyError("Musikdienst unbekannt")
        if not self.is_linked(sid, dev.household_id):
            raise ValueError(f"{info['name']} ist noch nicht verbunden – unter Räume › Musikdienste verbinden")
        with self._lock:
            if sid not in self._services:
                self._services[sid] = MusicService(info["name"], token_store=self._store(), device=dev)
            return self._services[sid]

    def link_begin(self, sid: str, dev: SoCo) -> str:
        info = self.catalog()[sid]
        ms = MusicService(info["name"], token_store=self._store(), device=dev)
        url = ms.begin_authentication()
        self._pending[sid] = ms
        return url

    def link_complete(self, sid: str) -> None:
        ms = self._pending.get(sid)
        if ms is None:
            raise ValueError("Bitte zuerst die Verknüpfung starten")
        try:
            ms.complete_authentication()
        except Exception as exc:  # noqa: BLE001 - Dienst meldet „noch nicht bestätigt“ unterschiedlich
            raise ValueError("Noch nicht bestätigt – bitte zuerst im Browser anmelden") from exc
        self._pending.pop(sid, None)
        self._services.pop(sid, None)
        if self.token_path.exists():
            os.chmod(self.token_path, 0o600)

    def unlink(self, sid: str, household: str) -> None:
        store = self._store()
        store._token_store.get(store.token_collection, {}).pop(f"{sid}#{household}", None)
        store.save_collection()
        os.chmod(self.token_path, 0o600)
        self._services.pop(sid, None)

    # ---------------------------------------------------------------- Durchsuchen
    def _to_item(self, sid: str, it) -> dict:
        md = it.metadata
        item_type = md.get("item_type") or "container"
        tm = md.get("track_metadata")
        tmd = tm.metadata if tm is not None else {}
        subtitle = " · ".join(x for x in (tmd.get("artist") or md.get("artist"), tmd.get("album")) if x)
        playable = bool(md.get("can_play")) or item_type in ("track", "stream", "program")
        container = item_type not in ("track", "stream", "program") and md.get("can_enumerate") is not False
        kind = {"artist": "musicArtist", "album": "musicAlbum", "playlist": "playlistContainer",
                "trackList": "playlistContainer", "program": "audioBroadcast", "stream": "audioBroadcast",
                "track": "musicTrack"}.get(item_type, "container")
        return {"id": make_id(sid, item_type, md["id"]), "title": md.get("title") or "",
                "subtitle": subtitle, "kind": kind, "container": container, "playable": playable,
                "art": tmd.get("album_art_uri") or md.get("album_art_uri"),
                "duration": tmd.get("duration")}

    def browse(self, dev: SoCo, item_id: str, start: int, count: int, search: str | None) -> dict:
        sid, _, smapi_id = split_id(item_id)
        ms = self.service(sid, dev)
        if search:
            cats = ms.available_search_categories or []
            cat = "all" if "all" in cats else (cats[0] if cats else "tracks")
            prefix = ms._get_search_prefix_map().get(cat, cat)
            raw = ms.soap_client.call("search", [("id", prefix), ("term", search), ("index", start), ("count", count)])
        else:
            raw = ms.soap_client.call("getMetadata", [("id", smapi_id), ("index", start), ("count", count), ("recursive", 0)])
        result = raw.get("searchResult") or raw.get("getMetadataResult") or {}
        dropped = self._drop_without_id(result)
        items = [self._to_item(sid, i) for i in parse_response(ms, raw, "browse")]
        try:
            total = int(result.get("total")) - dropped
        except (TypeError, ValueError):
            total = start + len(items) + (count if len(items) == count else 0)
        return {"items": items, "total": max(total, start + len(items))}

    @staticmethod
    def _drop_without_id(result: dict) -> int:
        """Spotify liefert Platzhalter ohne ID („Unable to access playlist“), an denen SoCo scheitert."""
        dropped = 0
        for key in ("mediaCollection", "mediaMetadata"):
            entries = result.get(key)
            if isinstance(entries, dict):
                entries = [entries]
            if entries is None:
                continue
            kept = [e for e in entries if e.get("id")]
            dropped += len(entries) - len(kept)
            result[key] = kept
        return dropped

    # ---------------------------------------------------------------- Abspielen
    def playable(self, dev: SoCo, item_id: str, title: str = "") -> tuple[str, str, bool]:
        """→ (uri, didl, ist_stream)"""
        sid, item_type, smapi_id = split_id(item_id)
        ms = self.service(sid, dev)
        info = self.catalog()[sid]
        st = info["type"]
        desc = f"SA_RINCON{st}_X_#Svc{st}-0-Token" if info["auth"] != "Anonymous" else f"SA_RINCON{st}_"
        qid = quote(smapi_id, safe="")
        if item_type == "track":
            prefix, cls = TRACK
            if smapi_id.startswith("spotify:"):
                uri = f"x-sonos-spotify:{qid}?sid={sid}&flags=8224&sn=0"
            else:
                uri = f"x-sonos-http:{qid}?sid={sid}&flags=8224&sn=0"
            stream = False
        elif item_type in ("stream", "program"):
            if smapi_id.startswith("spotify:artistRadio"):
                prefix, cls = "100c206c", "object.item.audioItem.audioBroadcast.#artistRadio"
                uri = f"x-sonosapi-radio:{qid}?sid={sid}&flags=8300&sn=0"
            else:
                prefix, cls = STREAM
                uri = f"x-sonosapi-{'stream' if item_type == 'stream' else 'radio'}:{qid}?sid={sid}&flags=8224&sn=0"
            stream = True
        else:
            prefix, cls = CONTAINER_TYPES.get(item_type, CONTAINER_TYPES["playlist"])
            uri = f"x-rincon-cpcontainer:{prefix}{qid}"
            stream = False
        if not title:
            try:
                title = ms.get_media_metadata(smapi_id).get("title", "") if item_type == "track" else ""
            except Exception:  # noqa: BLE001 - Titel ist nur Anzeige
                title = ""
        didl = DIDL.format(id=f"{prefix}{qid}", title=escape(title or smapi_id), cls=cls, desc=desc)
        return uri, didl, stream

    # ---------------------------------------------------------------- Cover-Suche
    def cover_for(self, dev: SoCo, artist: str, album: str) -> str | None:
        """Album-Cover über einen verbundenen Dienst suchen (für Titel eingestellter Dienste wie Google Play Music)."""
        key = f"{artist}|{album}".lower()
        cache_path = self.token_path.parent / "covers.json"
        with self._lock:
            if not hasattr(self, "_cover_cache"):
                try:
                    self._cover_cache = json.loads(cache_path.read_text())
                except (OSError, ValueError):
                    self._cover_cache = {}
            if key in self._cover_cache:
                return self._cover_cache[key]
        url = None
        sid = next((s for s in ("9",) if self.is_linked(s, dev.household_id)), None)
        if sid and (artist or album):
            try:
                with self._search_lock:  # die SOAP-Verbindung verträgt keine parallelen Anfragen
                    res = self.service(sid, dev).search("albums", f"{album} {artist}".strip(), 0, 1)
                first = next(iter(res), None)
                url = first.metadata.get("album_art_uri") if first is not None else None
            except Exception:  # noqa: BLE001 - Cover sind nur Deko
                return None
        with self._lock:
            self._cover_cache[key] = url
            cache_path.write_text(json.dumps(self._cover_cache, ensure_ascii=False))
        return url

    # ---------------------------------------------------------------- Favoriten-Ordner
    def favorite_target(self, fav) -> str | None:
        """Ordner-Favorit (ohne Abspieladresse) → svc-ID zum Durchsuchen."""
        try:
            from soco.data_structures_entry import from_didl_string
            ref = from_didl_string(fav.resource_meta_data)[0]
        except Exception:  # noqa: BLE001
            return None
        desc = getattr(ref, "desc", "") or ""
        if not desc.startswith("SA_RINCON"):
            return None
        sid = self.sid_for_type(desc[len("SA_RINCON"):].split("_", 1)[0])
        if not sid:
            return None
        raw = ref.item_id[8:] if len(ref.item_id) > 8 else ref.item_id
        smapi_id = unquote(raw)
        item_type = "artist" if "musicArtist" in ref.item_class else "container"
        return make_id(sid, item_type, smapi_id)
