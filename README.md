# Starclip

Local short-form editor for your own videos. Drop clips into a folder, describe the cut in a storyboard, and render one output with ffmpeg.

## Prerequisite

Starclip shells out to [ffmpeg](https://ffmpeg.org/). Install it and make sure the `ffmpeg` command is on your `PATH` before you render.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

`pip install -e .` is enough if you only want the `starclip` command.

## Run

Put your footage in `clips/`, then point a storyboard at those files. A starting point is in `storyboard.example.json`.

```bash
starclip render storyboard.example.json --dry-run
starclip render storyboard.example.json
```

`--dry-run` prints the ffmpeg command without running it or requiring the clip files to exist. A real render writes the cut to the `output` path in the storyboard (under `renders/` in the example).

Each storyboard entry is a clip file, an in point, an out point, and an optional caption.

## Footage stays out of the repo

Commit the tool, not the videos. `clips/` (except `.gitkeep`), `renders/`, `.env`, and common video/audio extensions are gitignored. Keep anything you did not shoot off this machine and out of version control.

## Roadmap

Milestones and issues for v0.1, v0.2, and v1.0 live on the [milestones page](https://github.com/jakobmusk/starclip/milestones).
