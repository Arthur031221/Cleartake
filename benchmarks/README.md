# Benchmark

What I measured, on which data, and how to repeat it.

## Setup

| Item | Value |
| --- | --- |
| Data | VoiceBank-DEMAND test set, 824 utterances at 16 kHz. I took every 8th one, 103 clips, speakers p232 and p257 |
| Variants | `noisy` (the input as it is), `classic` and `studio` at strength 1.0 and no loudness step |
| Quality score | DNSMOS P.835 through `speechmos`, mean over the clips: OVRL (overall), SIG (speech), BAK (background) |
| Word error | Whisper `base.en` transcript of each variant against the Whisper transcript of the clean recording, `jiwer` WER on lowercase words without punctuation |
| Drift rate | the number the app shows: words that differ between the noisy transcript and the variant transcript, divided by the words in the noisy transcript |
| Speed | audio seconds per wall second for the enhancement stage alone, GPU warm, clips of 1.2 to 6.5 seconds (mean 2.4), which includes the fixed cost of each call |
| Machine | RTX 5090, PyTorch from `clearvoice`, Python 3.12 |

Reproduce it with `uv pip install speechmos jiwer` and `python benchmarks/run.py --every 8`. It takes about 8 minutes on
a GPU. The raw output is in [`results.json`](results.json).

## Results

| Variant | OVRL | SIG | BAK | WER vs clean transcript | Drift rate vs noisy | Speed |
| --- | --- | --- | --- | --- | --- | --- |
| noisy | 2.59 | 3.22 | 2.98 | 5.4% | n/a | n/a |
| classic | 3.17 | 3.44 | 4.06 | 5.1% | 7.0% | 12.7x |
| studio | 3.14 | 3.40 | 4.08 | 6.6% | 7.7% | 13.8x |

## How to read this

* DNSMOS rises on every axis, mostly through the background score. That is the part a denoiser should move.
* Word error does not improve. VoiceBank-DEMAND is mild noise and Whisper already reads it well (5.4% against the
  clean transcript), so the enhancer has little to fix and some room to hurt. Studio ends 1.2 points above the noisy
  input and classic 0.3 points below it. On 103 clips a difference of one point is a handful of words, so treat the
  gap between the two engines as unresolved.
* The drift rate of about 7% is not an error rate. It counts every word Whisper writes differently, including
  spelling variants and words the noisy version got wrong. It is the reason the word check lists changes instead
  of scoring them.
* Two runs of the same command gave studio drift rates of 7.4% and 7.7%, and classic WER of 5.7% and 5.1%. Classic is
  not bit exact between runs, and the Whisper pass moves a little as well. Expect about half a point of noise.
* Speed is for the enhancement stage. A whole file also pays for decoding, the loudness pass and the word check.
  A 76 second video took 6.6 seconds end to end without the word check, 11.5x realtime.

## CPU

One 25 second clip on 3 CPU cores (`--device cpu --no-check`), wall time for the whole run: classic 35.7 s (0.7x
realtime) and studio 8.0 s (3.2x realtime). Classic is slower than studio on a CPU in my runs, so the classic engine is
not a speed option. Pick it when you want to stay within an 8 kHz speech band.

## Not covered

Other languages, music, reverberant rooms, and any noise type outside the DEMAND set. DNSMOS is a learned
predictor, not a listening test.
