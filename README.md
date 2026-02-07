# Color-Frame-Analyzer

This repo is a small, repeatable workflow for extracting frames from videos (and normalizing still images), then filtering those frames to highlight specific colors/logos.

## Disclaimer

This is a **general-purpose** tool and can be used for anything. I simply developed it for a specific case first (reviewing footage around the September 10, 2025 Charlie Kirk event) and used it for visual pattern-hunting (for example, whether similar shirt colors appear repeatedly across footage).

This project does **not** accuse or identify anyone, and it does **not** claim proof of intent, coordination, or causation. If you use it, do so responsibly: avoid harassment/doxxing/misidentification, respect privacy, and only process media you have rights/permission to use.

### Privacy / responsible use

- Don’t use this project to identify, “track”, or target real people.
- Don’t post/upload frames that include faces, names, license plates, addresses, or other personal data.
- Don’t use outputs as “evidence” of someone’s identity or intent; color matches are noisy (lighting/compression can shift results).
- Follow local laws and platform rules, and only process media you have the rights/permission to use.

## What it does

1. **Frame extraction** (`script/extract_frames.py`)
   - Reads media from `Videos/` and `Images/`.
   - Extracts every Nth frame from each video using `ffmpeg` (default stride is `15`).
   - Converts each still image into a PNG.
   - Writes everything to `Extracted Frames/` as `frame_000001.png`, `frame_000002.png`, ...

2. **Color-based filtering / highlighting** (`script/filter_dark_red_frames.py`)
   - Scans `Extracted Frames/`.
   - Builds an HSV mask for a dark maroon/burgundy target color band (seeded from a few sample hex colors).
   - Keeps only frames with enough matching pixels and at least one sufficiently large connected region.
  - Writes results to `Post-Processed/` where non-matching pixels are grayscale and matching regions remain in color (making shirts/logos "pop").

## Folder layout

- `Videos/` — input videos (`.mp4`, `.mov`, `.mkv`, `.avi`, `.m4v`, `.webm`)
- `Images/` — input stills (`.png`, `.jpg`, `.jpeg`, `.bmp`, `.tif`, `.tiff`, `.gif`)
- `Extracted Frames/` — output from extraction (`frame_*.png`)
- `Post-Processed/` — output from filtering/highlighting
- `script/` — Python scripts
On a fresh checkout, the scripts will create `Videos/`, `Images/`, `Extracted Frames/`, and `Post-Proccessed/` automatically. You still need to bring your own media and put files into `Videos/` and/or `Images/`.
On a fresh checkout, the scripts will create `Videos/`, `Images/`, `Extracted Frames/`, and `Post-Processed/` automatically. You still need to bring your own media and put files into `Videos/` and/or `Images/`.

## Requirements

- **Python 3** (a virtual environment is recommended)
- **ffmpeg** on your `PATH` (the extractor also uses `ffprobe` if present for progress estimation)
- Python packages for the filter step:
  - `opencv-python`
  - `numpy`

## Quick start (PowerShell)

```powershell
# (Optional) create + activate a venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# install deps for the filter script
pip install opencv-python numpy

# 1) Extract frames from Videos/ and normalize Images/
python .\script\extract_frames.py

# 2) Keep/highlight frames matching the target dark-red range
python .\script\filter_dark_red_frames.py
```

### Resume mode (don't clear outputs)

By default, extraction clears `Extracted Frames/` before writing. To keep what you already have and append new frames:

```powershell
python .\script\extract_frames.py --no-clear
```

## Tuning

The key knobs are currently constants inside the scripts:

- `script/extract_frames.py`
  - `FRAME_STRIDE` — higher = fewer frames (faster), lower = more frames (slower)
- `script/filter_dark_red_frames.py`
  - `SAMPLE_HEX` — the seed colors for the target maroon/burgundy range
  - `MIN_PIXELS` — minimum total matching pixels in a frame to keep it
  - `MIN_CLUSTER_PIXELS` — minimum connected-region size to count as a valid match

If you want to search for a different shirt color, update `SAMPLE_HEX` (and possibly the margins) and rerun the filter step.

## Notes / caveats

- Lighting, camera auto white-balance, compression, and stage LEDs can shift colors; treat matches as leads to review, not definitive IDs.
- This is intended for offline review. Be careful about privacy and avoid doxxing/misidentification.

## License

See `LICENSE`.
