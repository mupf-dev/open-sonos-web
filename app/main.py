"""Web-Oberfläche für Sonos: REST-API + statisches Frontend."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import requests
from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from soco.exceptions import SoCoException, SoCoUPnPException

from . import media_info
from .demo_service import DemoService
from .sonos_service import NotConnected, SonosService

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
STATIC = Path(__file__).resolve().parent.parent / "static"

svc = DemoService() if os.environ.get("SONOS_DEMO", "").lower() in ("1", "true", "yes") else SonosService()
app = FastAPI(title="Sonos Web", docs_url="/api/docs", openapi_url="/api/openapi.json")


@app.exception_handler(Exception)
async def errors(_: Request, exc: Exception):
    if isinstance(exc, NotConnected):
        return JSONResponse({"error": str(exc)}, status_code=503)
    if isinstance(exc, KeyError):
        return JSONResponse({"error": str(exc.args[0]) if exc.args else "Nicht gefunden"}, status_code=404)
    if isinstance(exc, SoCoUPnPException):
        return JSONResponse({"error": f"Sonos lehnt die Aktion ab ({exc.error_code})"}, status_code=400)
    if isinstance(exc, (ValueError, SoCoException)):
        return JSONResponse({"error": str(exc)}, status_code=400)
    if isinstance(exc, requests.RequestException):
        return JSONResponse({"error": "Lautsprecher nicht erreichbar"}, status_code=503)
    logging.getLogger("sonos").exception("Unerwarteter Fehler")
    return JSONResponse({"error": "Interner Fehler"}, status_code=500)


def call(fn, *args, **kwargs):
    return run_in_threadpool(fn, *args, **kwargs)


async def ok(fn, *args, **kwargs):
    await call(fn, *args, **kwargs)
    return {"ok": True}


# ---------------------------------------------------------------- System
@app.get("/api/system")
async def system():
    return await call(svc.system)


@app.post("/api/system/hosts")
async def add_host(host: str = Body(..., embed=True)):
    return await call(svc.add_host, host.strip())


@app.delete("/api/system/hosts/{host}")
async def remove_host(host: str):
    return await call(svc.remove_host, host)


@app.get("/api/media/lyrics")
async def lyrics(artist: str, title: str, album: str = "", duration: int = 0):
    if svc.demo:
        return svc.lyrics(artist, title, duration) or {}
    return await call(media_info.lyrics, artist, title, album, duration) or {}


@app.get("/api/media/video")
async def music_video(artist: str, title: str, duration: int = 0):
    if svc.demo:
        return []
    return await call(media_info.video, artist, title, duration)


@app.get("/api/media/artist")
async def artist(name: str):
    if svc.demo:
        return svc.artist_info(name) or {}
    return await call(media_info.artist_info, name) or {}


@app.get("/api/prefs")
async def prefs():
    return await call(svc.prefs)


@app.put("/api/prefs")
async def set_prefs(body: dict = Body(...)):
    return await call(svc.set_prefs, body)


@app.post("/api/system/scan")
async def scan(network: str | None = Body(None, embed=True)):
    return await call(svc.scan, network or None)


@app.get("/api/state")
async def state():
    return await call(svc.state)


@app.get("/api/speakers")
async def speakers():
    return await call(svc.speaker_list)


@app.get("/api/art")
async def art(u: str):
    if not svc.is_speaker_url(u):
        raise HTTPException(400, "Nur Bilder vom Lautsprecher erlaubt")
    r = await call(requests.get, u, timeout=5)
    return Response(r.content, media_type=r.headers.get("content-type", "image/jpeg"),
                    headers={"Cache-Control": "public, max-age=86400"})


# ---------------------------------------------------------------- Wiedergabe
@app.post("/api/zones/{uid}/{action}")
async def transport(uid: str, action: str, body: dict = Body(default_factory=dict)):
    if action in ("play", "pause", "stop", "next", "previous"):
        return await ok(svc.transport, uid, action)
    if action == "seek":
        return await ok(svc.seek, uid, int(body["position"]))
    if action == "playmode":
        return await ok(svc.set_play_mode, uid, bool(body.get("shuffle")), body.get("repeat", "off"))
    if action == "crossfade":
        return await ok(svc.set_crossfade, uid, bool(body.get("enabled")))
    if action == "sleep":
        return await ok(svc.set_sleep, uid, body.get("minutes"))
    if action == "volume":
        return await ok(svc.set_volume, uid, body.get("volume"), body.get("mute"), body.get("relative"))
    if action == "group-volume":
        return await ok(svc.set_group_volume, uid, body.get("volume"), body.get("mute"))
    if action == "source":
        return await ok(svc.switch_source, uid, body.get("source", "linein"))
    if action == "join":
        return await ok(svc.join, uid, body["target"])
    if action == "unjoin":
        return await ok(svc.unjoin, uid)
    if action == "group":
        return await ok(svc.set_group, uid, list(body.get("members", [])))
    if action == "party":
        return await ok(svc.party, uid)
    if action == "play-item":
        return await ok(svc.play_item, uid, body["id"], body.get("mode", "replace"), body.get("title", ""))
    if action == "queue":
        return await ok(svc.queue_action, uid, body["action"], body.get("index"), body.get("to"), body.get("title"))
    raise HTTPException(404, "Unbekannte Aktion")


@app.post("/api/ungroup-all")
async def ungroup_all():
    return await ok(svc.ungroup_all)


@app.get("/api/zones/{uid}/queue")
async def queue(uid: str, start: int = 0, count: int = 200):
    return await call(svc.queue, uid, start, min(count, 500))


# ---------------------------------------------------------------- Inhalte
@app.get("/api/zones/{uid}/favorites")
async def favorites(uid: str):
    return await call(svc.favorites, uid)


@app.get("/api/zones/{uid}/services")
async def services(uid: str):
    return await call(svc.services, uid)


@app.post("/api/zones/{uid}/services/{sid}/{step}")
async def service_link(uid: str, sid: str, step: str):
    return await call(svc.service_link, uid, sid, step)


@app.get("/api/zones/{uid}/playlists")
async def playlists(uid: str):
    return await call(svc.playlists, uid)


@app.delete("/api/zones/{uid}/playlists/{pid:path}")
async def delete_playlist(uid: str, pid: str):
    return await ok(svc.delete_playlist, uid, pid)


@app.patch("/api/zones/{uid}/playlists/{pid:path}")
async def rename_playlist(uid: str, pid: str, title: str = Body(..., embed=True)):
    return await ok(svc.rename_playlist, uid, pid, title.strip())


@app.post("/api/zones/{uid}/playlist-add")
async def add_to_playlist(uid: str, playlist: str = Body(...), item: str = Body(...)):
    return await ok(svc.add_to_playlist, uid, playlist, item)


@app.get("/api/zones/{uid}/browse")
async def browse(uid: str, id: str, start: int = 0, count: int = 100, search: str | None = None):
    return await call(svc.browse, uid, id, start, min(count, 500), search or None)


@app.post("/api/zones/{uid}/library-update")
async def library_update(uid: str):
    return await ok(svc.library_update, uid)


# ---------------------------------------------------------------- Einstellungen & Wecker
@app.get("/api/speakers/{uid}/settings")
async def settings(uid: str):
    return await call(svc.settings, uid)


@app.patch("/api/speakers/{uid}/settings")
async def update_settings(uid: str, body: dict = Body(...)):
    return await ok(svc.update_settings, uid, body)


@app.get("/api/alarms")
async def alarms():
    return await call(svc.alarms)


@app.post("/api/alarms")
async def create_alarm(body: dict = Body(...)):
    return await ok(svc.save_alarm, body)


@app.put("/api/alarms/{alarm_id}")
async def update_alarm(alarm_id: str, body: dict = Body(...)):
    return await ok(svc.save_alarm, body, alarm_id)


@app.delete("/api/alarms/{alarm_id}")
async def delete_alarm(alarm_id: str):
    return await ok(svc.delete_alarm, alarm_id)


# ---------------------------------------------------------------- Frontend
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})
