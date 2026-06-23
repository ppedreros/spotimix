"""Era playlist management.

An *era* is a time-bounded playlist owned by the host account.  New songs
accumulate into the currently active era.  Creating a new era makes it the
active one from that point forward.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from src.spotify_client import get_host_client

load_dotenv()

logger = logging.getLogger(__name__)

HOST_USER_ID = os.getenv("HOST_USER_ID")
ERAS_PATH = Path(__file__).resolve().parent.parent / "data" / "eras.json"


def _load_eras() -> list[dict]:
    if ERAS_PATH.exists():
        return json.loads(ERAS_PATH.read_text(encoding="utf-8"))
    return []


def _save_eras(eras: list[dict]) -> None:
    ERAS_PATH.parent.mkdir(parents=True, exist_ok=True)
    ERAS_PATH.write_text(json.dumps(eras, indent=2, ensure_ascii=False), encoding="utf-8")


def get_active_era() -> dict | None:
    """Return the most recently created era, or ``None`` if no eras exist."""
    eras = _load_eras()
    if not eras:
        return None
    # Sort by created_at descending and return the newest.
    return max(eras, key=lambda e: e["created_at"])


def create_era(name: str | None = None) -> dict:
    """Create a new era playlist under the host account and persist it.

    Parameters
    ----------
    name:
        Optional playlist name.  Defaults to ``"Era — YYYY-MM-DD"``.

    Returns
    -------
    dict
        The era record that was saved to ``data/eras.json``.
    """
    now = datetime.now(timezone.utc)
    playlist_name = name or f"Era — {now.strftime('%Y-%m-%d')}"

    sp = get_host_client()
    playlist = sp._post(
    "me/playlists",
    payload={
        "name": playlist_name,
        "public": True,
        "description": f"SpotiMix era playlist created on {now.strftime('%B %d, %Y')}",
    },
)

    era_record = {
        "playlist_id": playlist["id"],
        "playlist_url": playlist["external_urls"]["spotify"],
        "name": playlist_name,
        "created_at": now.isoformat(),
    }

    eras = _load_eras()
    eras.append(era_record)
    _save_eras(eras)

    logger.info("Created new era: %s (%s)", playlist_name, playlist["id"])
    print(f"\n🎵  New era created: {playlist_name}")
    print(f"    Playlist URL: {era_record['playlist_url']}\n")

    return era_record
