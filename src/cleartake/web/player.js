// Plays the original and the result in lock step and switches between them with a short gain ramp,
// so toggling never skips or restarts.
export class ABPlayer {
  constructor(original, enhanced) {
    this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    this.buffers = { original, enhanced };
    this.duration = Math.min(original.duration, enhanced.duration);
    this.mode = "enhanced";
    this.region = null;
    this.looping = false;
    this.playing = false;
    this.offset = 0;
    this.startedAt = 0;
  }

  get position() {
    if (!this.playing) return this.offset;
    let pos = this.offset + (this.ctx.currentTime - this.startedAt);
    if (this.looping && this.region && pos >= this.region[1]) {
      const span = this.region[1] - this.region[0];
      pos = this.region[0] + ((pos - this.region[0]) % span);
    }
    return Math.min(pos, this.duration);
  }

  async play(from = this.offset) {
    await this.ctx.resume();
    this.stopSources();
    const [lo, hi] = this.region || [0, this.duration];
    this.offset = from >= this.duration - 0.02 ? lo : from;
    this.sources = {};
    this.gains = {};
    for (const key of ["original", "enhanced"]) {
      const source = this.ctx.createBufferSource(), gain = this.ctx.createGain();
      source.buffer = this.buffers[key];
      gain.gain.value = key === this.mode ? 1 : 0;
      source.connect(gain).connect(this.ctx.destination);
      if (this.looping && this.region) { source.loop = true; source.loopStart = lo; source.loopEnd = hi; }
      source.start(0, this.offset);
      this.sources[key] = source; this.gains[key] = gain;
    }
    this.sources.enhanced.onended = () => {
      if (this.playing && !this.looping && this.position >= this.duration - 0.05) this.stop(0);
    };
    this.startedAt = this.ctx.currentTime;
    this.playing = true;
  }

  stopSources() {
    for (const source of Object.values(this.sources || {})) { source.onended = null; try { source.stop(); } catch {} }
    this.sources = {};
  }

  dispose() { this.stop(); this.ctx.close().catch(() => {}); }
  pause() { this.offset = this.position; this.playing = false; this.stopSources(); }
  stop(to = 0) { this.playing = false; this.stopSources(); this.offset = to; }
  seek(time) { const t = Math.min(Math.max(time, 0), this.duration); this.playing ? this.play(t) : (this.offset = t); }

  setMode(mode) {
    this.mode = mode;
    if (!this.playing) return;
    const now = this.ctx.currentTime;
    for (const key of ["original", "enhanced"]) this.gains[key].gain.setTargetAtTime(key === mode ? 1 : 0, now, 0.006);
  }

  setRegion(region, looping) {
    this.region = region; this.looping = looping && !!region;
    if (this.playing) this.play(this.position);
  }
}
