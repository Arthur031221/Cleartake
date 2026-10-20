# Configuration

Cleartake has no config file. Everything is a flag or one of two environment variables.

| Setting | Where | Default |
| --- | --- | --- |
| Model and cache folder | `CLEARTAKE_HOME` | `~/.cache/cleartake` |
| Whisper model cache | the Hugging Face cache, `HF_HOME` moves it | `~/.cache/huggingface` |
| Engine, strength, preset, format | CLI flags, see [usage](usage.md) | studio, 1.0, podcast, auto |
| GPU or CPU | `--device cpu` on the CLI and on `serve` | GPU when PyTorch sees one |
| Web app address | `cleartake serve --host H --port P` | `127.0.0.1:8765` |
| Upload limit | `cleartake serve --max-upload-mb N`, refused while the body streams in | 2048 |
| Finished jobs kept by the web app | fixed, `KEEP_FINISHED_JOBS` in `server.py` | 12 |

## Loudness presets

| Preset | Integrated loudness | True peak ceiling |
| --- | --- | --- |
| podcast | -16 LUFS | -1.5 dBTP |
| youtube | -14 LUFS | -1.5 dBTP |
| broadcast | -23 LUFS | -1.0 dBTP |

The table lives in `src/cleartake/loudness.py` as `PRESETS`. Add a row there and the CLI and the API accept the new preset.
The web app has a fixed list, so add an `<option>` to the `#preset` select in `index.html` as well.

## Web app language and theme

The page picks its language from the browser and remembers a manual choice in `localStorage`
(`cleartake.lang`). The theme follows the system and is stored as `cleartake.theme`. Locale files live in
`src/cleartake/web/locales/`, one JSON file per language with the same keys as `en.json`.
A test fails when a locale misses a key or drops a placeholder.

## HTTP API

The web app is a thin client for these routes, so you can script it.

| Route | Purpose |
| --- | --- |
| `GET /api/health` | version, device, ffmpeg, engines and whether each is downloaded |
| `POST /api/jobs` | multipart `file` plus `engine`, `strength`, `preset`, `check`, returns `202` and a job id |
| `GET /api/jobs/{id}` | state (`queued`, `running`, `done`, `error`), current stage, report |
| `GET /api/jobs/{id}/original.wav`, `enhanced.wav` | the two previews |
| `GET /api/jobs/{id}/download` | the finished file |
| `GET /api/jobs/{id}/report.json` | the report |

Jobs run one at a time on a single worker, in the order they arrive.
