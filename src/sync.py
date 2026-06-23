"""Weekly sync job.

For each connected user, fetches their "On Repeat" playlist, diffs the
tracks against the active era playlist, and adds only new (deduplicated)
tracks.
"""

import json
import logging
from pathlib import Path

from src.eras import get_active_era
from src.spotify_client import get_client, get_host_client

logger = logging.getLogger(__name__)

USERS_PATH = Path(__file__).resolve().parent.parent / "data" / "users.json"

# Spotify's "On Repeat" playlist is owned by the "spotify" account.
ON_REPEAT_OWNER = "spotify"
ON_REPEAT_NAMES = {"On Repeat", "En repetición", "En bucle", "Im Repeat"}

def _load_users() -> list[dict]:
    if USERS_PATH.exists():
        return json.loads(USERS_PATH.read_text(encoding="utf-8"))
    return []


def _find_on_repeat(sp) -> dict | None:
    offset = 0
    limit = 50

    while True:
        playlists = sp.current_user_playlists(limit=limit, offset=offset)
        for pl in playlists["items"]:
            logger.info("  🔍 Found Spotify playlist: '%s'", pl["name"])
            if pl["name"] in ON_REPEAT_NAMES:
                return pl
        if playlists["next"] is None:
            break
        offset += limit

    return None


def _get_playlist_track_uris(sp, playlist_id: str) -> set[str]:
    """Return a set of all track URIs in the given playlist."""
    uris: set[str] = set()
    offset = 0
    limit = 100

    while True:
        results = sp.playlist_items(
            playlist_id,
            fields="items(track(uri)),next",
            limit=limit,
            offset=offset,
        )
        for item in results.get("items", []):
            track = item.get("track")
            if track and track.get("uri"):
                uris.add(track["uri"])
        if results.get("next") is None:
            break
        offset += limit

    return uris


def _add_tracks_to_playlist(sp, playlist_id: str, uris: list[str]) -> None:
    """Add tracks to a playlist in batches of 100 (Spotify API limit)."""
    batch_size = 100
    for i in range(0, len(uris), batch_size):
        batch = uris[i : i + batch_size]
        sp.playlist_add_items(playlist_id, batch)


def sync() -> None:
    """Run the sync job: pull each user's "On Repeat" and add new tracks to
    the active era playlist."""
    active_era = get_active_era()
    if not active_era:
        print("⚠️  No active era found. Create one first with: python main.py new-era")
        return

    era_playlist_id = active_era["playlist_id"]
    users = _load_users()

    if not users:
        print("⚠️  No users onboarded yet. Add users with: python main.py onboard")
        return

    # Get the current tracks already in the era playlist (for dedup).
    host_sp = get_host_client()
    existing_uris = _get_playlist_track_uris(host_sp, era_playlist_id)

    total_added = 0

    for user in users:
        display_name = user.get("display_name", user["user_id"])
        logger.info("Syncing user: %s", display_name)

        try:
            sp = get_client(user["refresh_token"], scope="playlist-read-private")
        except Exception:
            logger.warning(
                "⚠️  Could not authenticate user %s — token may be stale or revoked. Skipping.",
                display_name,
            )
            continue

        # Find the "On Repeat" playlist.
        on_repeat = _find_on_repeat(sp)
        if not on_repeat:
            logger.info("  ℹ️  No 'On Repeat' playlist found for %s. Skipping.", display_name)
            continue

        # Get the user's current "On Repeat" tracks.
        user_uris = _get_playlist_track_uris(sp, on_repeat["id"])
        new_uris = user_uris - existing_uris

        if not new_uris:
            logger.info("  ✓  %s — no new tracks.", display_name)
            print(f"  ✓  {display_name} — no new tracks")
            continue

        new_uris_list = sorted(new_uris)  # deterministic order
        _add_tracks_to_playlist(host_sp, era_playlist_id, new_uris_list)

        # Update existing_uris so subsequent users don't duplicate.
        existing_uris.update(new_uris)
        total_added += len(new_uris_list)

        logger.info("  ✚  %s — added %d new track(s).", display_name, len(new_uris_list))
        print(f"  ✚  {display_name} — added {len(new_uris_list)} new track(s)")

    print(f"\n🎶  Sync complete. {total_added} new track(s) added to era: {active_era['name']}")
