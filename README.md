# SpotiMix — Spotify Era Playlist Accumulator

SpotiMix automatically accumulates songs from multiple Spotify users' **"On Repeat"** playlists into shared **era playlists** owned by a single host account.

## How It Works

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  User A      │     │  User B      │     │  User C      │
│  "On Repeat" │     │  "On Repeat" │     │  "On Repeat" │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └────────────┬───────┘────────────────────┘
                    ▼
           ┌────────────────┐
           │  Weekly Sync   │
           │  (dedup + diff)│
           └───────┬────────┘
                   ▼
         ┌──────────────────┐
         │  Active Era      │
         │  Playlist (host) │
         └──────────────────┘
```

- Multiple users connect their Spotify accounts once via OAuth.
- A weekly job pulls each user's current "On Repeat" playlist.
- New tracks (not already in the active era playlist) get added to it.
- The **host account** owns all era playlists.
- At any point you can create a **new era** — from that moment, new songs accumulate there instead.
- Tracks are deduplicated by Spotify URI (no duplicates within a single era).

---

## Prerequisites

- **Python 3.10+**
- A [Spotify Developer App](https://developer.spotify.com/dashboard) with:
  - A **Client ID** and **Client Secret**
  - A **Redirect URI** set to `http://127.0.0.1:8888/callback`

---

## Setup

### 1. Clone and install dependencies

```bash
git clone <your-repo-url>
cd spotimix
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

| Variable               | Description                                                  |
|------------------------|--------------------------------------------------------------|
| `SPOTIFY_CLIENT_ID`    | Your Spotify app's Client ID                                 |
| `SPOTIFY_CLIENT_SECRET`| Your Spotify app's Client Secret                             |
| `SPOTIFY_REDIRECT_URI` | Must match what's registered in Spotify (default: `http://127.0.0.1:8888/callback`) |
| `HOST_USER_ID`         | Your Spotify user ID (the account that owns era playlists)   |

> **Tip:** Find your Spotify user ID at [spotify.com/account](https://www.spotify.com/account/) or from the URI of your profile page.

### 3. Onboard the host account

The host account needs `playlist-modify-public` and `playlist-modify-private` scopes:

```bash
python main.py onboard --host
```

A browser will open for you to authorize. After authorizing, the refresh token is saved to `data/users.json`.

### 4. Create your first era

```bash
python main.py new-era "Summer 2026"
```

This creates a public playlist under your host account and marks it as the active era.

---

## Usage

### Onboard a new user

Each friend/guest just needs to run the onboard command once:

```bash
python main.py onboard
```

They'll be prompted to open a Spotify authorization URL. After granting access (the `playlist-read-private` scope), their refresh token is saved locally.

### Run the weekly sync

```bash
python main.py sync
```

This will:
1. Iterate over all onboarded users.
2. Find each user's "On Repeat" playlist (the one owned by Spotify).
3. Diff the tracks against the current active era playlist.
4. Add only new, deduplicated tracks to the era playlist.

If a user's token is stale or revoked, they are skipped with a warning — the sync never crashes.

### Create a new era

```bash
python main.py new-era                   # Auto-named "Era — 2026-06-22"
python main.py new-era "Fall Vibes"      # Custom name
```

From this point forward, all new tracks accumulate in the new era playlist.

---

## Automate with cron

Add a cron job to run the sync weekly (e.g., every Sunday at 2 AM):

```bash
crontab -e
```

```cron
0 2 * * 0 cd /path/to/spotimix && /path/to/python main.py sync >> /var/log/spotimix.log 2>&1
```

On **Windows**, use Task Scheduler instead:

```powershell
schtasks /create /tn "SpotiMix Sync" /tr "python C:\path\to\spotimix\main.py sync" /sc weekly /d SUN /st 02:00
```

---

## Project Structure

```
spotimix/
├── main.py                  # CLI entry point (onboard, sync, new-era)
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variable template
├── .gitignore
├── data/
│   ├── users.json           # Onboarded users + refresh tokens
│   └── eras.json            # Era playlists + metadata
└── src/
    ├── __init__.py
    ├── auth.py              # OAuth onboarding flow
    ├── sync.py              # Weekly sync job
    ├── eras.py              # Era playlist creation
    └── spotify_client.py    # Shared spotipy client helper
```

---

## Data Files

### `data/users.json`

```json
[
  {
    "user_id": "spotify_user_id",
    "display_name": "Pablo",
    "refresh_token": "AQD..."
  }
]
```

### `data/eras.json`

```json
[
  {
    "playlist_id": "3cEYpjA9oz9GiPac4AsH4n",
    "playlist_url": "https://open.spotify.com/playlist/3cEYpjA9oz9GiPac4AsH4n",
    "name": "Summer 2026",
    "created_at": "2026-06-22T17:00:00+00:00"
  }
]
```

---

## Security Notes

- **Never commit `.env`** — it contains your Spotify app secrets.
- **`data/users.json` contains refresh tokens** — treat it as sensitive. It's included in `.gitignore` by default if you don't want it tracked.
- Refresh tokens are long-lived but can be revoked by the user at any time in their [Spotify account settings](https://www.spotify.com/account/apps/).

---

## License

MIT
