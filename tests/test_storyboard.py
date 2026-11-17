"""Smoke tests for storyboard validation and ffmpeg command building."""

from __future__ import annotations

from pathlib import Path

import pytest

from starclip.ffmpeg import FFmpegNotFoundError, build_ffmpeg_command, find_ffmpeg
from starclip.storyboard import StoryboardError, load_storyboard, parse_storyboard


def valid_payload(**overrides):
    data = {
        "output": "renders/out.mp4",
        "clips": [
            {"file": "clips/example1.mp4", "in": 0, "out": 2, "caption": "Hook"},
            {"file": "clips/example2.mp4", "in": 1.5, "out": 4, "caption": "Payoff"},
        ],
    }
    data.update(overrides)
    return data


def test_parse_valid_storyboard_in_dry_run():
    storyboard = parse_storyboard(valid_payload(), dry_run=True)
    assert len(storyboard.clips) == 2
    assert storyboard.clips[0].in_point == 0
    assert storyboard.clips[0].out_point == 2
    assert storyboard.clips[0].caption == "Hook"
    assert storyboard.output.name == "out.mp4"


def test_rejects_in_not_less_than_out():
    payload = valid_payload()
    payload["clips"][0]["out"] = 0
    with pytest.raises(StoryboardError, match="in point"):
        parse_storyboard(payload, dry_run=True)


def test_rejects_equal_in_and_out():
    payload = valid_payload()
    payload["clips"][0]["in"] = 2
    payload["clips"][0]["out"] = 2
    with pytest.raises(StoryboardError, match="in point"):
        parse_storyboard(payload, dry_run=True)


def test_rejects_negative_times():
    payload = valid_payload()
    payload["clips"][0]["in"] = -1
    with pytest.raises(StoryboardError, match="non-negative"):
        parse_storyboard(payload, dry_run=True)


def test_caption_is_optional():
    payload = valid_payload()
    del payload["clips"][1]["caption"]
    storyboard = parse_storyboard(payload, dry_run=True)
    assert storyboard.clips[1].caption is None


def test_rejects_non_string_caption():
    payload = valid_payload()
    payload["clips"][0]["caption"] = 123
    with pytest.raises(StoryboardError, match="caption"):
        parse_storyboard(payload, dry_run=True)


def test_missing_file_rejected_unless_dry_run(tmp_path: Path):
    payload = valid_payload()
    with pytest.raises(StoryboardError, match="does not exist"):
        parse_storyboard(payload, base=tmp_path, dry_run=False)

    parse_storyboard(payload, base=tmp_path, dry_run=True)

    clips_dir = tmp_path / "clips"
    clips_dir.mkdir()
    (clips_dir / "example1.mp4").write_bytes(b"")
    (clips_dir / "example2.mp4").write_bytes(b"")
    storyboard = parse_storyboard(payload, base=tmp_path, dry_run=False)
    assert storyboard.clips[0].file.is_file()


def test_load_storyboard_from_example_in_dry_run():
    path = Path(__file__).resolve().parents[1] / "storyboard.example.json"
    storyboard = load_storyboard(path, dry_run=True)
    assert len(storyboard.clips) == 2
    assert storyboard.clips[0].caption == "Hook"
    assert storyboard.output.name == "example.mp4"


def test_build_ffmpeg_command_trims_captions_and_concats():
    storyboard = parse_storyboard(valid_payload(), dry_run=True)
    command = build_ffmpeg_command(storyboard, ffmpeg="ffmpeg")
    assert command[0] == "ffmpeg"
    # Each clip is trimmed with input -ss/-to before -i.
    i_indexes = [i for i, part in enumerate(command) if part == "-i"]
    assert len(i_indexes) == 2
    for i_index in i_indexes:
        assert command[i_index - 4] == "-ss"
        assert command[i_index - 2] == "-to"
    assert command[i_indexes[0] - 3] == "0"
    assert command[i_indexes[0] - 1] == "2"
    assert command[i_indexes[1] - 3] == "1.5"
    assert command[i_indexes[1] - 1] == "4"

    filter_complex = command[command.index("-filter_complex") + 1]
    assert "drawtext=" in filter_complex
    assert "text='Hook'" in filter_complex
    assert "text='Payoff'" in filter_complex
    assert "concat=n=2:v=1:a=1[vout][aout]" in filter_complex
    assert str(storyboard.output) == command[-1]


def test_build_skips_drawtext_when_no_caption():
    payload = valid_payload()
    payload["clips"] = [{"file": "clips/example1.mp4", "in": 0, "out": 2}]
    storyboard = parse_storyboard(payload, dry_run=True)
    command = build_ffmpeg_command(storyboard, ffmpeg="ffmpeg")
    filter_complex = command[command.index("-filter_complex") + 1]
    assert "drawtext=" not in filter_complex
    assert "concat=n=1:v=1:a=1[vout][aout]" in filter_complex


def test_find_ffmpeg_missing(monkeypatch):
    monkeypatch.setattr("starclip.ffmpeg.shutil.which", lambda _name: None)
    with pytest.raises(FFmpegNotFoundError, match="ffmpeg was not found"):
        find_ffmpeg()
