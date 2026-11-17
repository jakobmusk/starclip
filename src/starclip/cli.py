"""Command-line interface for Starclip."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

from starclip.ffmpeg import FFmpegNotFoundError, build_ffmpeg_command, find_ffmpeg
from starclip.storyboard import StoryboardError, load_storyboard


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="starclip",
        description="Cut clips to a storyboard and render them with ffmpeg.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    render = subparsers.add_parser(
        "render", help="Render a storyboard to a single output video."
    )
    render.add_argument("storyboard", type=Path, help="Path to a storyboard JSON file.")
    render.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the ffmpeg command without running it.",
    )

    args = parser.parse_args(argv)
    if args.command == "render":
        return _render(args.storyboard, dry_run=args.dry_run)
    parser.error(f"Unknown command: {args.command}")
    return 2


def _render(path: Path, *, dry_run: bool) -> int:
    try:
        storyboard = load_storyboard(path, dry_run=dry_run)
        command = build_ffmpeg_command(storyboard, ffmpeg=find_ffmpeg())
    except StoryboardError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except FFmpegNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if dry_run:
        print(shlex.join(command))
        return 0

    storyboard.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"error: ffmpeg exited with status {exc.returncode}", file=sys.stderr)
        return exc.returncode or 1

    print(f"Wrote {storyboard.output}")
    return 0
