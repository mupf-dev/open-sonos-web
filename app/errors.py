"""Fehler mit Code statt fertigem Text – die Oberfläche übersetzt den Code (static/i18n/*.json, Schlüssel „err.<code>“).

Der englische Text hier dient als Rückfall für API-Nutzer und unbekannte Codes.
"""

from __future__ import annotations

MESSAGES = {
    "not_connected": "No Sonos system reachable",
    "speaker_unknown": "Unknown speaker",
    "item_not_found": "Item not found",
    "item_not_playable": "This item cannot be played",
    "favorite_not_found": "Favorite not found",
    "favorite_folder": "“{title}” is a folder of a music service that is not linked here",
    "playlist_not_found": "Playlist not found",
    "alarm_not_found": "Alarm not found",
    "invalid_recurrence": "Invalid recurrence",
    "invalid_ip": "Please enter a valid IP address",
    "unknown_setting": "Unknown setting: {key}",
    "service_unknown": "Unknown music service",
    "service_not_linked": "{name} is not linked yet – link it under Rooms › Music services",
    "link_not_started": "Please start linking first",
    "link_not_confirmed": "Not confirmed yet – please sign in in your browser first",
    "demo_unavailable": "Not available in demo mode",
    "art_forbidden": "Only images from your speakers are allowed",
    "unknown_action": "Unknown action",
    "speaker_unreachable": "Speaker not reachable",
    "rejected": "Sonos rejected the action ({code})",
    "internal": "Internal error",
}


class AppError(Exception):
    def __init__(self, code: str, status: int = 400, **params) -> None:
        self.code, self.status, self.params = code, status, params
        super().__init__(message(code, params))


def message(code: str, params: dict | None = None) -> str:
    text = MESSAGES.get(code, code)
    try:
        return text.format(**(params or {}))
    except (KeyError, IndexError):
        return text


def payload(code: str, params: dict | None = None) -> dict:
    return {"error": message(code, params), "code": code, "params": params or {}}
