"""Load and validate a Starclip storyboard."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class StoryboardError(ValueError):
    """Invalid storyboard contents or a missing clip file."""


@dataclass(frozen=True)
class Clip:
    file: Path
    in_point: float
    out_point: float
    caption: str | None


@dataclass(frozen=True)
class Storyboard:
    output: Path
    clips: list[Clip]


def load_storyboard(path: Path | str, *, dry_run: bool = False) -> Storyboard:
    """Load a storyboard JSON file and validate its clips."""
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StoryboardError(f"Storyboard not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise StoryboardError(f"Storyboard is not valid JSON: {path}") from exc
    return parse_storyboard(raw, base=path.parent, dry_run=dry_run)


def parse_storyboard(
    raw: Any, *, base: Path | None = None, dry_run: bool = False
) -> Storyboard:
    """Parse a storyboard object. Clip files may be missing when dry_run is true."""
    base = Path.cwd() if base is None else Path(base)
    if not isinstance(raw, dict):
        raise StoryboardError("Storyboard must be a JSON object.")

    output = raw.get("output")
    if not output or not isinstance(output, str):
        raise StoryboardError('Storyboard must include a string "output" path.')

    clips_raw = raw.get("clips")
    if not isinstance(clips_raw, list) or not clips_raw:
        raise StoryboardError('Storyboard must include a non-empty "clips" array.')

    clips = [
        _parse_clip(item, index=index, base=base, dry_run=dry_run)
        for index, item in enumerate(clips_raw)
    ]
    return Storyboard(output=_resolve(base, output), clips=clips)


def _parse_clip(item: Any, *, index: int, base: Path, dry_run: bool) -> Clip:
    label = f"clips[{index}]"
    if not isinstance(item, dict):
        raise StoryboardError(f"{label} must be an object.")

    file_value = item.get("file")
    if not file_value or not isinstance(file_value, str):
        raise StoryboardError(f'{label} must include a string "file" path.')

    in_point = _parse_time(item.get("in"), field=f"{label}.in")
    out_point = _parse_time(item.get("out"), field=f"{label}.out")
    if in_point < 0 or out_point < 0:
        raise StoryboardError(f"{label} times must be non-negative.")
    if in_point >= out_point:
        raise StoryboardError(
            f"{label} in point ({in_point}) must be less than out point ({out_point})."
        )

    caption = item.get("caption")
    if caption is not None and not isinstance(caption, str):
        raise StoryboardError(f"{label}.caption must be a string if provided.")
    if caption == "":
        caption = None

    clip_path = _resolve(base, file_value)
    if not dry_run and not clip_path.is_file():
        raise StoryboardError(f"{label} file does not exist: {clip_path}")

    return Clip(
        file=clip_path,
        in_point=in_point,
        out_point=out_point,
        caption=caption,
    )


def _parse_time(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise StoryboardError(f"{field} must be a number.")
    return float(value)


def _resolve(base: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = base / path
    return path
