# Changelog

## 0.2.0

* The web app has a Spoken language menu for the word check: English, 18 other languages or automatic detection. English keeps `base.en` and everything else uses the multilingual Whisper `small`. The server refuses a language it does not offer
* The hosted demo no longer tells you to drop a file when it can only play the sample, and its card has no blank band above the button

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
* Web app takes several files at once: one row per file with upload progress, queue position and a cancel button, Review and Download on finished rows
* `DELETE /api/jobs/{id}` cancels a waiting or running job (a running one stops after its current step) and removes a finished one
* A finished job the page polled in the last five minutes is not pruned during a long batch, and a job that vanished from the server shows an error instead of a spinner
* Keyboard and screen reader use: transcript words are buttons, arrow keys seek when the picture has focus, the Play and Pause label follows the language, and only the progress title is announced
* Each release tag builds the wheel, checks that the web app and all locales are inside it, and attaches it to the GitHub release
