# Architecture

Cleartake is one pipeline with two front ends, a CLI and a local web app, plus a static copy of the web app that
runs from a pre-rendered sample.

```
 file -> decode -> enhance -> finish -> check -> write
          ffmpeg     model       loudness   whisper    wav, flac, m4a, mp3
          48 kHz     blend       limiter    diff       or video with the
          mono       strength    ebur128               picture copied
```

## Modules

| File | Job |
| --- | --- |
| `media.py` | probe, decode to 48 kHz mono float, encode, mux video, md5 of the video packets |
| `engines.py` | the two models behind one `Engine.enhance(audio)` interface, plus the strength blend |
| `loudness.py` | EBU R128 measurement through ffmpeg `ebur128`, gain, `alimiter` for the true peak |
| `drift.py` | faster-whisper transcription, difflib alignment, the list of changed words |
| `pipeline.py` | `run(source, options)` ties the stages together and builds the report |
| `cli.py` | argument parsing, batch mode, `serve`, `doctor` |
| `server.py` | FastAPI app, one worker thread, an in-memory job table, file results in a temp folder |
| `web/` | the interface: plain ES modules, no build step |

## Decisions

**Two engines, one interface.** Both are ClearerVoice-Studio checkpoints (Apache-2.0): FRCRN at 16 kHz as
`classic` and MossFormer2 at 48 kHz as `studio`. The `clearvoice` package resolves its checkpoint folder relative
to the working directory, so `engines.py` changes into `CLEARTAKE_HOME/models` while it loads a model.
DeepFilterNet was my first choice and I dropped it because its Rust extension has no wheel for Python 3.12 and
a plain `uv tool install` should not need a Rust toolchain.

**Loudness after enhancement.** A denoiser changes the level, so the preset is applied to the enhanced signal and
measured again on the file that was written, so the report shows what an mp3 or AAC encode did to the level.
The report holds both measurements.

**Video keeps its picture.** Only the audio goes through the models. The picture stream is copied with
`-c:v copy`, and the md5 of the video packets before and after is compared. `picture_kept` is true only on a match.

**The word check is a second opinion, not a metric.** It runs Whisper on both versions and aligns the words. It
cannot say which version is right. See [usage](usage.md) for what it over reports.

**The server guards itself.** A page on another site can POST a form to 127.0.0.1, and a rebinding DNS name can
read the API. `Guard` in `server.py` checks the Host header, compares a browser Origin with the Host, and counts
body bytes as they arrive so an oversized upload is refused before it fills the disk. Finished jobs beyond the
newest 12 are deleted.

**One worker.** The models are large and a GPU does not gain from two jobs at once, so `server.py` keeps one
thread and a queue. The page shows the queue position. Cancel sets a flag that `on_stage` turns into a `Cancelled`
exception at the next stage boundary, so the unwinding goes through the same path as any other failure.

**No build step in the UI.** `web/` is HTML, CSS and ES modules served as they are. The same files are copied to
GitHub Pages. When `/api/health` does not answer, `app.js` switches to demo mode and loads
`demo/original.mp3`, `demo/enhanced.mp3` and `demo/report.json`.

## The A and B player

Both versions are decoded once with Web Audio and kept in memory. Switching A and B swaps gain nodes with a short
ramp, so playback continues from the same position without a click. The spectrogram is drawn per column from an
FFT of the decoded samples.

## Tests

| Layer | Where | Needs |
| --- | --- | --- |
| Unit | `tests/test_*.py` | ffmpeg, no models. A `FakeEngine` stands in for the neural nets |
| Browser end to end | `tests/e2e/` | Chrome or Chromium through Playwright, the real FastAPI app with the fake engine, the static demo site |
| Real models | `pytest -m model` | the downloaded models, run by hand and in the manual CI job |
| Benchmark | `benchmarks/run.py` | the models, `speechmos`, `jiwer`, the VoiceBank-DEMAND test set |
