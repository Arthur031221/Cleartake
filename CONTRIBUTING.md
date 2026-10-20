# Contributing

Bug reports with a file that reproduces the problem are the most useful thing you can send. If the file is private,
a 10 second excerpt cut with `ffmpeg -ss 0 -t 10 -i in.wav out.wav` is enough.

## Set up

```bash
git clone https://github.com/Arthur031221/Cleartake
cd Cleartake
uv venv && uv pip install -e ".[dev]"
.venv/bin/python -m playwright install chromium   # only for the browser tests
```

You need ffmpeg on PATH. The unit tests use a fake engine, so they run without a GPU and without model downloads.

## Before you open a pull request

```bash
.venv/bin/ruff format . && .venv/bin/ruff check .
.venv/bin/python -m pytest              # unit and browser tests
.venv/bin/python -m pytest -m model     # real models, optional, downloads about 0.5 GB
```

## Rules of thumb

* A change to enhancement, loudness or the word check needs a test, and the README numbers that depend on it need a
  rerun of `benchmarks/run.py`.
* New interface text goes into `src/cleartake/web/locales/en.json` first. Add the key to every other locale as well.
  A machine translation is fine when you say so in the pull request. The locale test checks keys and placeholders.
* Keep the web app free of a build step and of runtime dependencies from a CDN.
* Docs and the README are plain English in the first person, without dashes, emoji or hype words.

## Ideas that are open

* macOS and Windows testing, including Apple GPU speed
* A Docker image
* More loudness presets
* A language aware normaliser for the word check (numbers, spelling variants)
