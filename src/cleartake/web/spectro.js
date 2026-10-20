// Spectrogram and waveform drawing. One FFT per pixel column, so a long file costs the same as a short one.
const FFT_SIZE = 2048;
const MAX_HZ = 16000;
const FLOOR_DB = -95;
const CEIL_DB = -25;

function fft(re, im) {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) { [re[i], re[j]] = [re[j], re[i]]; [im[i], im[j]] = [im[j], im[i]]; }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const angle = (-2 * Math.PI) / len;
    const wr = Math.cos(angle), wi = Math.sin(angle);
    for (let i = 0; i < n; i += len) {
      let cr = 1, ci = 0;
      for (let k = 0; k < len / 2; k++) {
        const a = i + k, b = a + len / 2;
        const tr = re[b] * cr - im[b] * ci, ti = re[b] * ci + im[b] * cr;
        re[b] = re[a] - tr; im[b] = im[a] - ti; re[a] += tr; im[a] += ti;
        const next = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = next;
      }
    }
  }
}

const PALETTE = [[21, 19, 15], [60, 34, 12], [150, 70, 10], [255, 176, 46], [255, 244, 214]];
function color(v) {
  const x = Math.min(Math.max(v, 0), 1) * (PALETTE.length - 1);
  const i = Math.min(Math.floor(x), PALETTE.length - 2), f = x - i;
  return PALETTE[i].map((c, k) => c + (PALETTE[i + 1][k] - c) * f);
}

export function drawSpectrogram(canvas, samples, sampleRate, width, height) {
  canvas.width = width; canvas.height = height;
  const ctx = canvas.getContext("2d");
  const image = ctx.createImageData(width, height);
  const window = new Float32Array(FFT_SIZE).map((_, i) => 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / (FFT_SIZE - 1)));
  const re = new Float32Array(FFT_SIZE), im = new Float32Array(FFT_SIZE);
  const bins = Math.min(FFT_SIZE / 2, Math.floor((MAX_HZ / sampleRate) * FFT_SIZE));
  const lut = Array.from({ length: 256 }, (_, i) => color(i / 255));
  for (let x = 0; x < width; x++) {
    const centre = Math.floor(((x + 0.5) / width) * samples.length) - FFT_SIZE / 2;
    for (let i = 0; i < FFT_SIZE; i++) {
      const s = samples[centre + i];
      re[i] = (s === undefined ? 0 : s) * window[i]; im[i] = 0;
    }
    fft(re, im);
    for (let y = 0; y < height; y++) {
      const bin = Math.min(bins - 1, Math.floor(((height - 1 - y) / height) * bins));
      const mag = Math.hypot(re[bin], im[bin]) / (FFT_SIZE / 4);
      const db = 20 * Math.log10(mag + 1e-9);
      const shade = lut[Math.round(255 * Math.min(Math.max((db - FLOOR_DB) / (CEIL_DB - FLOOR_DB), 0), 1))];
      const p = (y * width + x) * 4;
      image.data[p] = shade[0]; image.data[p + 1] = shade[1]; image.data[p + 2] = shade[2]; image.data[p + 3] = 255;
    }
  }
  ctx.putImageData(image, 0, 0);
}

export function drawWaveform(canvas, samples, width, height, rgb = "255, 176, 46") {
  canvas.width = width; canvas.height = height;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = `rgba(${rgb}, 0.9)`;
  const per = samples.length / width;
  for (let x = 0; x < width; x++) {
    let lo = 0, hi = 0;
    const start = Math.floor(x * per), end = Math.min(samples.length, Math.floor((x + 1) * per) + 1);
    for (let i = start; i < end; i += Math.max(1, Math.floor((end - start) / 64))) {
      if (samples[i] < lo) lo = samples[i];
      if (samples[i] > hi) hi = samples[i];
    }
    const top = height / 2 - Math.min(hi, 1) * (height / 2), bottom = height / 2 - Math.max(lo, -1) * (height / 2);
    ctx.fillRect(x, top, 1, Math.max(1, bottom - top));
  }
}
