/**
 * Strlix barge-in VAD AudioWorkletProcessor (feature-flagged).
 *
 * Posts { type: 'vad', rms, voiceMs, barge: bool } to the main thread.
 * Falls back path lives in static/index.html (AnalyserNode + getUserMedia AEC).
 * This worklet does NOT replace Azure Speech /ws/stt — it only improves
 * barge-gate timing when STRLIX_BARGE_WORKLET=1 / ?bargeWorklet=1.
 */
class BargeVadProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    const opts = (options && options.processorOptions) || {};
    this._floor = typeof opts.floor === 'number' ? opts.floor : 0.004;
    this._voiceMs = 0;
    this._requiredMs = typeof opts.requiredMs === 'number' ? opts.requiredMs : 90;
    this._aecOn = opts.aec !== false;
    this._guardUntil = currentTime + (opts.guardSec || 0.22);
    this._lastPost = 0;
    this.port.onmessage = (ev) => {
      const m = ev.data || {};
      if (m.type === 'reset') {
        this._voiceMs = 0;
        this._floor = 0.004;
        this._guardUntil = currentTime + (m.guardSec || 0.22);
      }
      if (m.type === 'config') {
        if (typeof m.requiredMs === 'number') this._requiredMs = m.requiredMs;
        if (typeof m.aec === 'boolean') this._aecOn = m.aec;
      }
    };
  }

  process(inputs) {
    const input = inputs[0] && inputs[0][0];
    if (!input || !input.length) return true;
    let sum = 0;
    for (let i = 0; i < input.length; i++) {
      const v = input[i];
      sum += v * v;
    }
    const rms = Math.sqrt(sum / input.length);
    const now = currentTime;
    // ~frame duration at 128 samples / sampleRate
    const dtMs = (input.length / sampleRate) * 1000;

    if (now < this._guardUntil) {
      if (now - this._lastPost > 0.05) {
        this.port.postMessage({ type: 'vad', rms, voiceMs: 0, barge: false, guard: true });
        this._lastPost = now;
      }
      return true;
    }

    if (rms < this._floor * 2) this._floor = this._floor * 0.97 + rms * 0.03;
    const threshold = Math.max(this._aecOn ? 0.045 : 0.09, this._floor * 3 + 0.012);
    this._voiceMs += rms > threshold ? dtMs : -dtMs * 1.5;
    if (this._voiceMs < 0) this._voiceMs = 0;
    const barge = this._voiceMs >= this._requiredMs;
    if (barge || now - this._lastPost > 0.05) {
      this.port.postMessage({
        type: 'vad',
        rms,
        floor: this._floor,
        threshold,
        voiceMs: this._voiceMs,
        barge,
      });
      this._lastPost = now;
    }
    if (barge) this._voiceMs = 0;
    return true;
  }
}

registerProcessor('barge-vad-processor', BargeVadProcessor);
