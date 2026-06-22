#!/usr/bin/env python3
"""SpotiMix — CLI entry point.

Usage:
    python main.py onboard [--host]   Add a new user (use --host for the host account)
    python main.py sync               Run the weekly sync job manually
    python main.py new-era [NAME]     Create a new era playlist
"""

import argparse
import logging
import sys

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def cmd_onboard(args: argparse.Namespace) -> None:
    from src.auth import onboard_user

    onboard_user(is_host=args.host)


def cmd_sync(_args: argparse.Namespace) -> None:
    from src.sync import sync

    sync()


def cmd_new_era(args: argparse.Namespace) -> None:
    from src.eras import create_era

    name = " ".join(args.name) if args.name else None
    create_era(name)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="spotimix",
        description="Spotify Era Playlist Accumulator — accumulate 'On Repeat' tracks into shared era playlists.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- onboard ---
    onboard_parser = subparsers.add_parser(
        "onboard",
        help="Onboard a new Spotify user via OAuth.",
    )
    onboard_parser.add_argument(
        "--host",
        action="store_true",
        help="Onboard the host account (grants playlist-modify scopes).",
    )
    onboard_parser.set_defaults(func=cmd_onboard)

    # --- sync ---
    sync_parser = subparsers.add_parser(
        "sync",
        help="Run the weekly sync: pull 'On Repeat' tracks and add to the active era.",
    )
    sync_parser.set_defaults(func=cmd_sync)

    # --- new-era ---
    new_era_parser = subparsers.add_parser(
        "new-era",
        help="Create a new era playlist under the host account.",
    )
    new_era_parser.add_argument(
        "name",
        nargs="*",
        help="Optional playlist name. Defaults to 'Era — YYYY-MM-DD'.",
    )
    new_era_parser.set_defaults(func=cmd_new_era)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
