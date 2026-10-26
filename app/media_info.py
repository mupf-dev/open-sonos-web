"""Zusatzinfos zum laufenden Titel aus freien Diensten ohne API-Schlüssel.

- Songtexte (wenn möglich zeitgenau): LRCLIB, https://lrclib.net
- Interpret (Kurzbeschreibung + Bild): Wikipedia (deutsch, sonst englisch)

Es werden nur Interpret, Titel, Album und Dauer übertragen. Ergebnisse werden im Speicher zwischengespeichert.
"""

from __future__ import annotations

import json
import re
import threading
from collections import OrderedDict
from urllib.parse import quote

import requests

HEADERS = {"User-Agent": "sonos-web/1.0 (lokale Sonos-Oberflaeche)"}
MUSIC_WORDS = re.compile(r"band|musik|sänger|rapper|dj|komponist|produzent|duo|gruppe|singer|musician|"
                         r"group|songwriter|producer|orchestra|orchester|ensemble|künstler", re.I)

_cache: OrderedDict[str, object] = OrderedDict()
_lock = threading.Lock()


class _Unavailable(Exception):
    """Dienst gerade nicht erreichbar – Ergebnis nicht zwischenspeichern."""


def _cached(key: str, fn):
    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
    try:
        value = fn()
    except _Unavailable:
        return None
    with _lock:
        _cache[key] = value
        while len(_cache) > 500:
            _cache.popitem(last=False)
    return value


def _clean_title(title: str) -> str:
    """„Numb - Remastered 2011“ / „Song (feat. X)“ → „Numb“ / „Song“."""
    title = re.sub(r"\s*[\(\[](feat\.?|ft\.?|with|mit)[^\)\]]*[\)\]]", "", title, flags=re.I)
    title = re.split(r"\s+-\s+", title)[0]
    return title.strip()


def _main_artist(artist: str) -> str:
    return re.split(r",|\s+feat\.?\s+|\s+ft\.?\s+|\s+x\s+", artist, flags=re.I)[0].strip()


# ---------------------------------------------------------------- Songtexte
def lyrics(artist: str, title: str, album: str = "", duration: int = 0) -> dict | None:
    if not artist or not title:
        return None
    return _cached(f"lyr|{artist}|{title}|{album}|{duration}", lambda: _fetch_lyrics(artist, title, album, duration))


def _fetch_lyrics(artist: str, title: str, album: str, duration: int) -> dict | None:
    params = {"artist_name": artist, "track_name": title}
    if album:
        params["album_name"] = album
    if duration:
        params["duration"] = duration
    data = None
    try:
        r = requests.get("https://lrclib.net/api/get", params=params, headers=HEADERS, timeout=6)
        if r.ok:
            data = r.json()
        elif r.status_code != 404:
            raise _Unavailable
        else:
            r = requests.get("https://lrclib.net/api/search", headers=HEADERS, timeout=6,
                             params={"artist_name": _main_artist(artist), "track_name": _clean_title(title)})
            if not r.ok:
                raise _Unavailable
            hits = r.json()
            # bevorzugt Treffer mit passender Länge und zeitgenauem Text
            hits.sort(key=lambda h: (not h.get("syncedLyrics"), abs((h.get("duration") or 0) - duration) if duration else 0))
            data = hits[0] if hits else None
    except (requests.RequestException, ValueError):
        raise _Unavailable from None
    if not data:
        return None
    return {"synced": data.get("syncedLyrics"), "plain": data.get("plainLyrics"),
            "instrumental": bool(data.get("instrumental")), "source": "LRCLIB"}


# ---------------------------------------------------------------- Interpret
def artist_info(name: str) -> dict | None:
    if not name:
        return None
    return _cached(f"art|{name}", lambda: _fetch_artist(name))


def _summary(lang: str, page: str) -> dict | None:
    try:
        r = requests.get(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(page.replace(' ', '_'))}",
                         headers=HEADERS, timeout=5)
    except requests.RequestException:
        raise _Unavailable from None
    if r.status_code == 404:
        return None
    if not r.ok:
        raise _Unavailable
    d = r.json()
    if d.get("type") != "standard":
        return None
    return d


def _fetch_artist(name: str) -> dict | None:
    names = [name] + ([_main_artist(name)] if _main_artist(name) != name else [])
    for lang, suffixes in (("de", ("(Band)", "(Musiker)", "(Rapper)", "(Sänger)", "(Sängerin)", "")),
                           ("en", ("(band)", "(musician)", "(rapper)", "(singer)", ""))):
        for n in names:
            for suffix in suffixes:
                d = _summary(lang, f"{n} {suffix}".strip())
                if not d:
                    continue
                text = f"{d.get('description') or ''} {d.get('extract') or ''}"
                if MUSIC_WORDS.search(text[:400]):
                    img = (d.get("originalimage") or d.get("thumbnail") or {}).get("source")
                    return {"name": d.get("title"), "description": d.get("description"), "extract": d.get("extract"),
                            "image": img, "url": (d.get("content_urls") or {}).get("desktop", {}).get("page"),
                            "source": f"Wikipedia ({lang})"}
    return None


# ---------------------------------------------------------------- Musikvideo (YouTube, ohne API-Schlüssel)
YT_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/130.0 Safari/537.36", "Accept-Language": "de-DE,de;q=0.9,en;q=0.8"}
GOOD = re.compile(r"official (music )?video|music video|offizielles (musik)?video|\(video\)|\[video\]", re.I)
BAD = re.compile(r"\b(audio|visuali[sz]er|lyrics?|karaoke|cover|reaction|live|8d|slowed|sped up|nightcore|"
                 r"instrumental|remix|1 hour|loop|tutorial)\b", re.I)


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9äöüß ]+", " ", text.lower()).strip()


def video(artist: str, title: str, duration: int = 0) -> list[dict]:
    """Passende YouTube-Videos, bestes zuerst (leer, wenn nichts eindeutig passt)."""
    if not artist or not title:
        return []
    return _cached(f"vid|{artist}|{title}|{duration}", lambda: _fetch_video(artist, title, duration)) or []


def _fetch_video(artist: str, title: str, duration: int) -> list[dict]:
    main, song = _main_artist(artist), _clean_title(title)
    try:
        r = requests.get("https://www.youtube.com/results", params={"search_query": f"{main} {song}", "hl": "de"},
                         headers=YT_HEADERS, cookies={"CONSENT": "YES+1", "SOCS": "CAI"}, timeout=8)
        m = re.search(r"var ytInitialData = (\{.*?\});</script>", r.text, re.S) if r.ok else None
        if not m:
            raise _Unavailable
        data = json.loads(m.group(1))
    except (requests.RequestException, ValueError):
        raise _Unavailable from None

    found: list[dict] = []

    def walk(o):
        if isinstance(o, dict):
            v = o.get("videoRenderer")
            if v and v.get("videoId"):
                found.append({
                    "id": v["videoId"],
                    "title": "".join(x.get("text", "") for x in v.get("title", {}).get("runs", [])),
                    "channel": (v.get("ownerText", {}).get("runs") or [{}])[0].get("text", ""),
                    "length": _length(v.get("lengthText", {}).get("simpleText")),
                })
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)

    walk(data)
    want_song, want_artist = _norm(song), _norm(main)
    song_words = [w for w in want_song.split() if len(w) > 1]
    results = []
    for v in found[:20]:
        if v["channel"].endswith(" - Topic"):
            continue  # automatisch erzeugte „Art Tracks“: nur ein Standbild des Covers
        vt, ch = _norm(v["title"]), _norm(v["channel"])
        if not song_words or not all(w in vt for w in song_words):
            continue
        if want_artist not in vt and want_artist not in ch.replace(" vevo", "").replace("vevo", ""):
            continue
        score = 0.0
        if GOOD.search(v["title"]):
            score += 3
        for word in BAD.findall(v["title"]):
            if word.lower() not in title.lower():
                score -= 3
        if duration and v["length"]:
            score -= abs(v["length"] - duration) / 20
        results.append({**v, "score": round(score, 2)})
    results.sort(key=lambda x: -x["score"])
    return results[:4]


def _length(text: str | None) -> int:
    if not text:
        return 0
    sec = 0
    for part in text.split(":"):
        sec = sec * 60 + int(part) if part.isdigit() else sec
    return sec
