# Changelog

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
