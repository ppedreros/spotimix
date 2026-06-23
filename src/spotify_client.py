"""Shared helper that returns an authenticated spotipy client given a refresh token."""

import os

import spotipy
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")


def get_client(refresh_token: str, scope: str | None = None) -> spotipy.Spotify:
    """Return an authenticated Spotify client by exchanging *refresh_token*
    for a fresh access token.

    Uses an in-memory cache to avoid stale ``.cache`` files interfering
    with token scopes.

    Parameters
    ----------
    refresh_token:
        A valid Spotify OAuth2 refresh token.
    scope:
        Optional scope string.  Only used when constructing the
        :class:`SpotifyOAuth` manager — the actual permissions depend on
        what was granted during the original authorization.
    """
    auth_manager = spotipy.SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=scope,
        cache_handler=spotipy.MemoryCacheHandler(),
    )

    # Exchange the refresh token for a fresh access token.
    token_info = auth_manager.refresh_access_token(refresh_token)

    return spotipy.Spotify(auth=token_info["access_token"])


def get_host_client() -> spotipy.Spotify:
    """Return a Spotify client authenticated as the host account.

    The host's refresh token is read from ``data/users.json`` — it is the
    entry whose ``user_id`` matches the ``HOST_USER_ID`` env var.  If no
    matching entry exists this falls back to ``SpotifyOAuth`` with the
    required host scopes so the token can be obtained interactively.
    """
    import json
    from pathlib import Path

    host_user_id = os.getenv("HOST_USER_ID")
    users_path = Path(__file__).resolve().parent.parent / "data" / "users.json"

    if users_path.exists():
        users = json.loads(users_path.read_text(encoding="utf-8"))
        for user in users:
            if user.get("user_id") == host_user_id:
                return get_client(
                    user["refresh_token"],
                    scope="playlist-modify-public playlist-modify-private playlist-read-private",
                )

    # Fallback: interactive OAuth for the host account
    auth_manager = spotipy.SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope="playlist-modify-public playlist-modify-private",
        cache_handler=spotipy.MemoryCacheHandler(),
    )
    return spotipy.Spotify(auth_manager=auth_manager)
