// Audio engine: a sampled piano (Tone.Sampler) plus a metronome that rides the
// Transport so it follows the tempo slider automatically.
//
// Tone is injected (imported once in main.js) so there is a single Tone instance
// and a single shared Transport across all modules.

export class Player {
  constructor(Tone) {
    this.Tone = Tone;
    this.sampler = null;
    this.click = null;
    this.metroId = null;
    this.metroBeat = 0;
    this.metronomeEnabled = false;
    this._loading = null;
  }

  /** Lazily load piano samples + click synth. Safe to call repeatedly. */
  load() {
    if (this._loading) return this._loading;
    const Tone = this.Tone;

    this.click = new Tone.Synth({
      oscillator: { type: "square" },
      envelope: { attack: 0.001, decay: 0.03, sustain: 0, release: 0.02 },
      volume: -8,
    }).toDestination();

    this.sampler = new Tone.Sampler({
      urls: {
        A2: "A2.mp3",
        C3: "C3.mp3",
        "D#3": "Ds3.mp3",
        "F#3": "Fs3.mp3",
        A3: "A3.mp3",
        C4: "C4.mp3",
        "D#4": "Ds4.mp3",
        "F#4": "Fs4.mp3",
        A4: "A4.mp3",
        C5: "C5.mp3",
        "D#5": "Ds5.mp3",
      },
      baseUrl: "./samples/",
      release: 1,
      volume: -4,
    }).toDestination();

    this._loading = Tone.loaded();
    return this._loading;
  }

  /** Play a single MIDI note for durSec seconds, scheduled at Transport `time`. */
  triggerNote(midi, durSec, time) {
    const noteName = this.Tone.Frequency(midi, "midi").toNote();
    this.sampler.triggerAttackRelease(noteName, Math.max(0.08, durSec), time);
  }

  setMetronomeEnabled(on) {
    this.metronomeEnabled = on;
  }

  /** Schedule a repeating quarter-note click on the Transport. */
  startMetronome(beatsPerBar) {
    this.stopMetronome();
    this.metroBeat = 0;
    this.metroId = this.Tone.getTransport().scheduleRepeat((time) => {
      if (!this.metronomeEnabled) {
        this.metroBeat++;
        return;
      }
      const accent = this.metroBeat % beatsPerBar === 0;
      this.click.triggerAttackRelease(accent ? "C6" : "G5", "32n", time);
      this.metroBeat++;
    }, "4n", 0);
  }

  stopMetronome() {
    if (this.metroId != null) {
      this.Tone.getTransport().clear(this.metroId);
      this.metroId = null;
    }
  }
}
