"""Build and locate the ffmpeg command used to render a storyboard."""

from __future__ import annotations

import shutil

from starclip.storyboard import Storyboard


class FFmpegNotFoundError(RuntimeError):
    """Raised when ffmpeg is not available on PATH."""


def find_ffmpeg() -> str:
    """Return the ffmpeg executable path, or raise a friendly error."""
    path = shutil.which("ffmpeg")
    if path is None:
        raise FFmpegNotFoundError(
            "ffmpeg was not found on your PATH. "
            "Install ffmpeg (https://ffmpeg.org/download.html) and make sure "
            "the ffmpeg command is available in this shell, then try again."
        )
    return path


def escape_drawtext(text: str) -> str:
    """Escape a caption so it is safe inside an ffmpeg drawtext filter."""
    return (
        text.replace("\\", r"\\")
        .replace("'", r"\'")
        .replace(":", r"\:")
        .replace("%", r"\%")
        .replace(",", r"\,")
    )


def build_ffmpeg_command(storyboard: Storyboard, *, ffmpeg: str = "ffmpeg") -> list[str]:
    """Build an ffmpeg command list: per-clip trim, optional drawtext, and concat."""
    command: list[str] = [ffmpeg, "-y", "-hide_banner"]
    for clip in storyboard.clips:
        command.extend(
            [
                "-ss",
                _format_time(clip.in_point),
                "-to",
                _format_time(clip.out_point),
                "-i",
                str(clip.file),
            ]
        )

    command.extend(
        [
            "-filter_complex",
            _build_filter_complex(storyboard),
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(storyboard.output),
        ]
    )
    return command


def _format_time(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return str(value)


def _build_filter_complex(storyboard: Storyboard) -> str:
    parts: list[str] = []
    concat_labels: list[str] = []
    for index, clip in enumerate(storyboard.clips):
        if clip.caption:
            text = escape_drawtext(clip.caption)
            video = (
                f"[{index}:v]setpts=PTS-STARTPTS,"
                f"drawtext=text='{text}':x=(w-text_w)/2:y=h-th-80:"
                f"fontsize=48:fontcolor=white:borderw=3:bordercolor=black[v{index}]"
            )
        else:
            video = f"[{index}:v]setpts=PTS-STARTPTS[v{index}]"
        audio = f"[{index}:a]asetpts=PTS-STARTPTS[a{index}]"
        parts.append(video)
        parts.append(audio)
        concat_labels.append(f"[v{index}][a{index}]")

    n = len(storyboard.clips)
    parts.append(f"{''.join(concat_labels)}concat=n={n}:v=1:a=1[vout][aout]")
    return ";".join(parts)
