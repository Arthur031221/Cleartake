# Usage

## One file

```bash
cleartake interview.mp4
```

The result lands next to the input as `interview.cleartake.mp4`. For a video the picture stream is copied
without re-encoding and the audio is replaced. Cleartake checks this by hashing the video packets before and
after, and the report says `picture_kept: true` only when the hashes match. Only the first video stream and the new audio are kept, so extra audio tracks and subtitles are dropped. Inputs in webm, m4v or avi come out as mkv.

## Several files or a folder

```bash
cleartake episodes/ -o cleaned/
cleartake a.wav b.m4a c.mp4 -o cleaned/
```

A folder is searched for wav, flac, mp3, m4a, aac, ogg, opus, mp4, mov, mkv, webm, m4v and avi files, and `-o` keeps the sub folder layout. Files that already end in
`.cleartake.<ext>` are skipped, so running the same command twice does not stack results.
Cleartake refuses to start when two inputs would write the same output file or when a result would replace its input. One failing file does not stop the rest, and the exit code is 1 if any file failed.

## Options

| Flag | Default | What it does |
| --- | --- | --- |
| `--engine classic` or `studio` | `studio` | classic runs a 16 kHz model, so the result keeps speech up to 8 kHz. studio works at 48 kHz |
| `--strength 0..1` | `1.0` | blends the original back in. 0.7 keeps 30 percent of the original |
| `--preset podcast`, `youtube`, `broadcast`, `none` | `podcast` | loudness target of -16, -14 or -23 LUFS, or no change |
| `--format auto`, `wav`, `flac`, `m4a`, `mp3` | `auto` | output container for audio inputs |
| `--audio-only` | off | write audio even when the input is a video |
| `--no-check` | off | skip the word check |
| `--whisper MODEL` | `base.en` | any faster-whisper model name, for example `small` or `large-v3` |
| `--language CODE` | auto | spoken language for the word check, for example `de` |
| `--device cpu` | auto | hide the GPU |
| `--json` | off | print the report on stdout (progress goes to stderr) |

Each run writes `<output>.json` with the loudness before and after, the model, the device, the speed and the
word differences.

## The loudness step

The preset sets an integrated loudness target and a true peak ceiling (podcast -16 LUFS and -1.5 dBTP). Gain is
applied first, then a limiter holds the ceiling. Quiet speech with high peaks can hit the ceiling before the
target, so the result may land a few tenths of a LU low. The report shows the measured values, not the target.

## The word check

Whisper transcribes the original and the result, and the two transcripts are aligned word by word. Every
difference is listed with a timestamp. This catches an enhancer that turns one word into another, but it also
reports differences that come from Whisper itself. Spelling variants ("defence" and "defense") count, and so do
words Whisper got wrong in the noisy original and right in the result. Small numbers written as digits or words
count as the same word. Read the list as a place to listen, not as a verdict.

## Web app

```bash
cleartake serve --open
```

Drop one or more files, pick an engine and a preset, press Enhance. Each file shows its upload progress and its place in the queue, and the cross on its row cancels it. A running file stops at the end of its current step, because a model call cannot be interrupted. With several files the list stays on screen and Review opens any finished one, with a Download link beside it. The result page has an A and B player (press B to
switch, Space to play, drag on the picture to loop a part), the spectrogram of both versions, the loudness
numbers and the transcript with changed words marked. Click a word to hear it, or tab to it and press Enter. With the picture focused, the arrow keys seek by 5 seconds.

The server listens on 127.0.0.1 only unless you pass `--host`. It has no login, so do not expose it to a network
you do not trust. It refuses requests whose Host header is not this machine and browser requests from another origin, and it stops an upload that passes `--max-upload-mb` while the body is still arriving. It keeps the newest 12 finished jobs and deletes older ones, except a job the page asked about in the last five minutes. The setup card has a Spoken language menu for the word check. English uses `base.en`. Any other language, or Detect automatically, uses the multilingual `small` model, which is about 460 MB and downloads on first use. The CLI takes any model and language with `--whisper` and `--language`.

## Check the setup

```bash
cleartake doctor
```

Prints the ffmpeg path, the device and whether each model is downloaded.
