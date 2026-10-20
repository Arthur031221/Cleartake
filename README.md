<h1 align="center">
  <img src="assets/logo.svg" width="72" alt=""><br>
  Cleartake
</h1>

<p align="center">
  <strong>Clean takes from noisy recordings, and a check that nobody's words changed.</strong>
</p>

<p align="center">
  <a href="https://github.com/Arthur031221/Cleartake/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/Arthur031221/Cleartake/ci.yml?style=flat-square&color=ffb02e&label=CI" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-ffb02e?style=flat-square" alt="MIT license"></a>
  <img src="https://img.shields.io/badge/python-3.10%20to%203.12-ffb02e?style=flat-square" alt="Python 3.10 to 3.12">
  <a href="https://arthur031221.github.io/Cleartake/"><img src="https://img.shields.io/badge/live%20demo-open-ffb02e?style=flat-square" alt="Live demo"></a>
</p>

<p align="center">
  English | <a href="README.zh-TW.md">zh-TW</a> | <a href="README.zh-CN.md">zh-CN</a> | <a href="README.ja.md">ja</a> | <a href="README.ko.md">ko</a> | <a href="README.es.md">es</a> | <a href="README.fr.md">fr</a> | <a href="README.de.md">de</a> | <a href="README.pt-BR.md">pt-BR</a>
</p>

<p align="center">
  <img src="assets/demo.gif" alt="Cleartake web app: drop a file, listen to before and after, see the word check" width="860">
</p>

I built Cleartake for recordings that are good except for the hiss, the fan and the room. It runs a speech
enhancement model on your machine, sets the loudness to a broadcast target and keeps the video picture byte for byte.
Then it transcribes the original and the result and shows you any word that changed. Nothing is uploaded.

```bash
uv tool install git+https://github.com/Arthur031221/Cleartake
cleartake serve --open
```

DNSMOS background score **2.98 to 4.08** and overall **2.59 to 3.14** on 103 VoiceBank-DEMAND test clips, with the
studio engine, enhancement stage alone at 13.8x realtime on one RTX 5090.<br>
<sub>Method: every 8th clip of the 824 test utterances, strength 1.0, no loudness step, DNSMOS P.835 through
`speechmos`, GPU warm. Word error did not improve on this mild noise. The full table and its caveats are in
[benchmarks/README.md](benchmarks/README.md).</sub>

## Before and after

One clip from the demo set (VoiceBank-DEMAND speaker p232, 28.4 seconds, 81 words), default settings, measured on the
files in [docs/demo](docs/demo).

| | Original | Cleartake | What it means |
| --- | --- | --- | --- |
| DNSMOS overall | 2.63 | 3.33 | predicted quality, 1 to 5 |
| DNSMOS speech | 3.46 | 3.54 | the voice itself barely moves |
| DNSMOS background | 2.86 | 4.14 | the noise is the part that goes away |
| Integrated loudness | -22.2 LUFS | -16.2 LUFS | podcast preset |
| True peak | -4.3 dBTP | -1.6 dBTP | ceiling is -1.5 |
| Words that changed | | 0 of 81 | Whisper `base.en`, aligned word by word |

A denoiser doesn't fix speech, and I don't pretend it does. Cleartake removes noise, then audits the result, so a changed word shows up
as a line in a report instead of a surprise on air. [Try it in the browser](https://arthur031221.github.io/Cleartake/).
The hosted page plays this same clip and runs nothing.

## The pipeline

```
 decode            enhance            finish             check              write
+----------+      +----------+      +----------+      +----------+      +----------+
| any file |  ->  | speech   |  ->  | loudness |  ->  | word     |  ->  | audio or |
| to 48 kHz|      | model    |      | and peak |      | drift    |      | video    |
| mono     |      | on-device|      | target   |      | report   |      | + JSON   |
+----------+      +----------+      +----------+      +----------+      +----------+
 cleartake in.mp4  --engine studio   --preset podcast  --whisper small   -o out/ --json
```

| What you're doing | Command | Key principle |
| --- | --- | --- |
| Clean one file | `cleartake interview.mp4` | The result sits next to the input and the input is never touched |
| Clean a folder | `cleartake episodes/ -o cleaned/` | One bad file doesn't stop the batch, and files already named `.cleartake` are skipped |
| Keep some of the room | `cleartake talk.wav --strength 0.7` | Blend the original back instead of choosing all or nothing |
| Hit a platform target | `cleartake talk.wav --preset youtube` | Gain first, limiter second, and the report shows what was measured |
| Skip the word check | `cleartake talk.wav --no-check` | The check costs a Whisper pass, so you can turn it off |
| Audit in another language | `cleartake talk.wav --language de --whisper small` | Use a model that can read what was said |
| Work in a browser | `cleartake serve --open` | A local web app: drop several files, cancel any of them, then compare with an A/B player, a spectrogram and the word list |
| Script it | `cleartake in.wav --json` | The report goes to stdout and progress goes to stderr |
| Check the setup | `cleartake doctor` | Prints ffmpeg, the device and which models are downloaded before you wait on a download |

## Install

You need Python 3.10 to 3.12 and ffmpeg. Cleartake isn't on PyPI yet.

```bash
uv tool install git+https://github.com/Arthur031221/Cleartake
cleartake doctor
cleartake your-recording.wav
```

The first run downloads the model you pick (about 210 MB for studio, 161 MB for classic) and Whisper `base.en` (about
141 MB). After that it runs offline. The tool environment was 6.2 GB on my machine because PyTorch ships its CUDA
libraries, and the wheel installed in 75 seconds.

<details>
<summary>pip</summary>

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install git+https://github.com/Arthur031221/Cleartake
```

</details>

<details>
<summary>From a clone, with the test tools</summary>

```bash
git clone https://github.com/Arthur031221/Cleartake
cd Cleartake
uv venv && uv pip install -e ".[dev]"
.venv/bin/pytest
```

</details>

<details>
<summary>ffmpeg</summary>

```bash
sudo apt install ffmpeg      # Debian, Ubuntu
brew install ffmpeg          # macOS
winget install Gyan.FFmpeg        # Windows
```

</details>

<details>
<summary>Where models and files go</summary>

Models live in `~/.cache/cleartake` (set `CLEARTAKE_HOME` to move them). The Whisper model sits in the Hugging Face
cache. Web uploads live in a temporary folder and the newest 12 finished jobs are kept. See [docs/config.md](docs/config.md).

</details>

## Parts, by stage

### Decode

* Any container ffmpeg reads goes in, and the working signal is 48 kHz mono float.
* A video keeps its picture with `-c:v copy`. Cleartake hashes the video packets before and after, and the report says
  `picture_kept: true` only when the hashes match. Only the first video stream and the new audio are kept, so extra
  audio tracks and subtitles are dropped.

### Enhance

* `studio` (default) is MossFormer2_SE_48K, full band, 48 kHz.
* `classic` is FRCRN_SE_16K. It keeps speech up to 8 kHz, so pick it when you want a band limited result. Don't pick it for speed: on 3 CPU cores it ran at 0.7x realtime against 3.2x for studio. Its benchmark scores match studio
  within the noise, and studio is the default for its full band and its CPU speed.
* Both come from [ClearerVoice-Studio](https://github.com/modelscope/ClearerVoice-Studio) under Apache-2.0.

### Finish

* EBU R128 integrated loudness measured by ffmpeg `ebur128`, then gain, then `alimiter`.
* Presets: podcast -16 LUFS, youtube -14, broadcast -23 with a -1.0 dBTP ceiling, or `none`.

### Check

* faster-whisper transcribes both versions on the CPU, and the two transcripts are aligned with `difflib`.
* Numbers from 0 to 20 count as the same word whether written as digits or words.
* Every difference is listed with a timestamp so you can listen to it. The web app marks them on the transcript.

### Write

* Audio goes out as wav, flac, m4a or mp3. A video goes out as mp4, mov or mkv to match the input, and webm, m4v and
  avi inputs come out as mkv.
* `<output>.json` records loudness before and after (measured on the written file), engine, device, speed and the word differences.

## Measured

103 VoiceBank-DEMAND clips, DNSMOS P.835 through `speechmos`, RTX 5090. Method and how to repeat it are in
[benchmarks/README.md](benchmarks/README.md).

| Variant | OVRL | SIG | BAK | WER vs clean transcript | Speed |
| --- | --- | --- | --- | --- | --- |
| noisy | 2.59 | 3.22 | 2.98 | 5.4% | n/a |
| classic | 3.17 | 3.44 | 4.06 | 5.1% | 12.7x |
| studio | 3.14 | 3.40 | 4.08 | 6.6% | 13.8x |

Other timings: a 76 second video took 6.6 seconds end to end without the word check (11.5x). One 25 second clip on
3 CPU cores took 8.0 seconds with studio and 35.7 seconds with classic.

## Limits I know about

* **Word error did not improve.** On this mild noise Whisper already reads the input well. Studio ended 1.2 points
  above the noisy input and classic 0.3 points below it, and on 103 clips I can't tell the two apart. Two runs of the
  same command moved by about half a point.
* **The word check is a place to listen, not a verdict.** It reports about 7% of words as different on the benchmark,
  and that figure includes spelling variants and words the noisy original got wrong. It won't catch a change
  Whisper can't hear.
* **The loudness target can be missed by about 0.5 LU** when the true peak ceiling stops the gain first.
* **Quality scores are predicted.** DNSMOS is a learned model, not a listening test, and I only ran English speech with
  the DEMAND noise types. Music, reverb and other languages aren't measured.
* **Only Linux was tested** (an RTX 5090 and 3 CPU cores, Python 3.10 and 3.12). macOS and Windows should work but I
  haven't run them. There's no Docker image yet.
* **The web app's word check in other languages is untested.** English uses Whisper `base.en`. Any other language you pick in the setup card, or Detect automatically, uses Whisper `small` (about 460 MB, downloaded once). I haven't measured its accuracy per language.
* **Batch mode needs distinct names.** `-o` keeps the folder layout of a folder input, and Cleartake refuses to start
  when two inputs would write the same file or when a result would replace its input.
* **It's a download of several gigabytes** because of PyTorch, and the first run needs the network for the models.

## Tests

```bash
uv pip install -e ".[dev]" && playwright install chromium
pytest                 # 82 tests, includes browser tests of the web app
pytest -m model        # 2 more that load the real models
ruff check . && ruff format --check .
```

The browser tests upload one file and several, cancel a waiting and a running job, toggle A/B, drive the player from the keyboard, switch language and theme, and tamper with a report
to check that changed words are marked. More in [docs/architecture.md](docs/architecture.md).

## Docs

[Install](docs/install.md) | [Usage](docs/usage.md) | [Config](docs/config.md) | [Architecture](docs/architecture.md) |
[Benchmark](benchmarks/README.md) | [Contributing](CONTRIBUTING.md) | [Changelog](CHANGELOG.md)

## Credits

* [ClearerVoice-Studio](https://github.com/modelscope/ClearerVoice-Studio) for the enhancement models (Apache-2.0).
* [faster-whisper](https://github.com/SYSTRAN/faster-whisper) and the Whisper model for the word check.
* [VoiceBank-DEMAND](https://doi.org/10.7488/ds/2117) (CC BY 4.0) for the demo clips and the benchmark.
* DNSMOS P.835 from Microsoft, run through `speechmos`.

MIT licensed. See [LICENSE](LICENSE).

Assisted by Claude/Codex.
