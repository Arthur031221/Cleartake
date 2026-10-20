# Changelog

## Unreleased

* Web app takes several files at once: one row per file with upload progress, queue position and a cancel button, Review and Download on finished rows
* `DELETE /api/jobs/{id}` cancels a waiting or running job and removes a finished one
* A job the page polled in the last five minutes is no longer pruned under a long batch
* Fixes: a job that vanished from the server now shows an error instead of an endless spinner, each result no longer leaks an audio context, B and Space no longer act while a form field has focus, the window redraws the spectrogram on resize, and the page no longer scrolls sideways on a phone
* Keyboard and screen reader use: transcript words are buttons, arrow keys seek when the picture has focus, the Play and Pause label follows the language, and only the progress title is announced
* Pages deploys on a push that changes the site instead of waiting for the tests, CI takes torch from the CPU index alone, a tagged release builds the wheel, checks it and attaches it

## 0.1.0

First release.

* `cleartake FILE...` for audio and video, batch mode for folders
* Two engines: classic (FRCRN, 16 kHz) and studio (MossFormer2, 48 kHz)
* Strength blend, loudness presets for podcast, youtube and broadcast, true peak limiter
* Video input keeps the picture stream, verified by a hash of the video packets
* Word check with Whisper, listing every changed, dropped or added word with its timestamp
* `cleartake serve`: local web app with an A and B player, spectrograms, the word check view, 9 languages, light and dark themes
* Hosted demo on GitHub Pages from a pre-rendered sample
* Benchmark on 103 VoiceBank-DEMAND clips
* Web server refuses foreign Host and Origin headers and oversized uploads while they stream, and keeps the newest 12 finished jobs
* Batch mode keeps the folder layout under `-o` and refuses output name collisions
