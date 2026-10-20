# Install

Cleartake needs Python 3.10 to 3.12 and ffmpeg. A GPU is optional.

## Requirements

| Piece | Why | Check |
| --- | --- | --- |
| Python 3.10 to 3.12 | runs the models | `python3 --version` |
| ffmpeg and ffprobe on PATH | decoding, loudness measurement, writing video | `ffmpeg -version` |
| About 7 GB of disk | the tool environment was 6.2 GB on Linux because PyTorch ships CUDA libraries, plus about 0.5 GB of models in `~/.cache/cleartake` | `du -sh ~/.local/share/uv/tools/cleartake` |
| An NVIDIA GPU (optional) | about 4 times faster than 3 CPU cores in my runs | `cleartake doctor` |

Install ffmpeg with `sudo apt install ffmpeg`, `brew install ffmpeg` or `winget install Gyan.FFmpeg`.

## Install the tool

```bash
uv tool install git+https://github.com/Arthur031221/Cleartake
cleartake doctor
```

`pip install git+https://github.com/Arthur031221/Cleartake` works too. Cleartake is not on PyPI yet.

The first run downloads the model you pick (the classic engine is about 160 MB, studio about 210 MB) and the
Whisper `base.en` model for the word check (about 140 MB). After that nothing touches the network.

## Install from a clone

```bash
git clone https://github.com/Arthur031221/Cleartake
cd Cleartake
uv venv && uv pip install -e ".[dev]"
.venv/bin/cleartake doctor
```

## What I tested

| System | Result |
| --- | --- |
| Ubuntu, RTX 5090, Python 3.12 | everything in the README, including a clean `uv tool install` from a built wheel |
| Ubuntu, 3 CPU cores, `--device cpu` | enhancement, video, web app |
| macOS, Windows | not tested yet. Apple GPU support is whatever PyTorch gives you |

## Uninstall

```bash
uv tool uninstall cleartake
rm -rf ~/.cache/cleartake
```
