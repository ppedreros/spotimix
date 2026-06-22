"""OAuth onboarding flow for new users.

Generates an authorization URL, waits for the user to authorize, handles the
callback redirect to extract the auth code, and persists the refresh token to
``data/users.json``.
"""

import json
import logging
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import spotipy
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
USERS_PATH = Path(__file__).resolve().parent.parent / "data" / "users.json"

# Guest users only need to read their private playlists (for "On Repeat").
GUEST_SCOPE = "playlist-read-private"

# Host account needs playlist-modify permissions.
HOST_SCOPE = "playlist-modify-public playlist-modify-private playlist-read-private"


def _load_users() -> list[dict]:
    if USERS_PATH.exists():
        return json.loads(USERS_PATH.read_text(encoding="utf-8"))
    return []


def _save_users(users: list[dict]) -> None:
    USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    USERS_PATH.write_text(json.dumps(users, indent=2, ensure_ascii=False), encoding="utf-8")


def _build_auth_manager(scope: str) -> spotipy.SpotifyOAuth:
    return spotipy.SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=scope,
        show_dialog=True,
    )


def generate_auth_url(*, is_host: bool = False) -> str:
    """Return a Spotify authorization URL the user should open in a browser."""
    scope = HOST_SCOPE if is_host else GUEST_SCOPE
    auth_manager = _build_auth_manager(scope)
    return auth_manager.get_authorize_url()


def _wait_for_callback() -> str:
    """Start a tiny HTTP server and wait for the OAuth redirect.

    Returns the full callback URL so we can extract the ``code`` parameter.
    """
    parsed_redirect = urlparse(REDIRECT_URI)
    host = parsed_redirect.hostname or "localhost"
    port = parsed_redirect.port or 8888

    callback_url: list[str] = []

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 — required override
            callback_url.append(f"http://{host}:{port}{self.path}")
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h2>&#10004; Authorization successful!</h2>"
                b"<p>You can close this tab and return to the terminal.</p>"
                b"</body></html>"
            )

        def log_message(self, format, *args):  # noqa: A002
            # Silence default request logging.
            pass

    server = HTTPServer((host, port), _Handler)
    logger.info("Waiting for Spotify callback on %s:%s …", host, port)
    server.handle_request()  # blocks until one request arrives
    server.server_close()

    return callback_url[0]


def onboard_user(*, is_host: bool = False) -> dict:
    """Run the full interactive onboarding flow for a single user.

    1. Print an auth URL for the user to open.
    2. Start a local HTTP server to capture the callback.
    3. Exchange the authorization code for tokens.
    4. Persist the user's refresh token to ``data/users.json``.

    Returns the saved user record.
    """
    scope = HOST_SCOPE if is_host else GUEST_SCOPE
    auth_manager = _build_auth_manager(scope)
    auth_url = auth_manager.get_authorize_url()

    print("\n🔗  Open this URL in your browser to authorize:\n")
    print(f"    {auth_url}\n")

    # Wait for redirect
    callback_url = _wait_for_callback()
    code = parse_qs(urlparse(callback_url).query).get("code", [None])[0]

    if not code:
        raise RuntimeError("No authorization code received in the callback.")

    # Exchange the code for an access + refresh token.
    token_info = auth_manager.get_access_token(code, as_dict=True)
    refresh_token = token_info["refresh_token"]

    # Fetch the user's profile to get their display name and ID.
    sp = spotipy.Spotify(auth=token_info["access_token"])
    profile = sp.current_user()
    user_id = profile["id"]
    display_name = profile.get("display_name") or user_id

    # Upsert in users.json
    users = _load_users()
    existing = next((u for u in users if u["user_id"] == user_id), None)

    if existing:
        existing["refresh_token"] = refresh_token
        existing["display_name"] = display_name
        print(f"🔄  Updated existing user: {display_name} ({user_id})")
    else:
        record = {
            "user_id": user_id,
            "display_name": display_name,
            "refresh_token": refresh_token,
        }
        users.append(record)
        existing = record
        print(f"✅  Onboarded new user: {display_name} ({user_id})")

    _save_users(users)
    return existing
