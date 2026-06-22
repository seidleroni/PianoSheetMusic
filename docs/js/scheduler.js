// Playback scheduler. Owns a Tone.Part built from a piece's JSON note events,
// plays each note through the Player, and advances the OSMD cursor in lockstep
// so the highlight always sits on the sounding note.
//
// Timing lives in musical units (bars:beats:sixteenths), so moving the BPM
// slider rescales everything automatically -- no need to rebuild the Part.

/** Convert an absolute beat position (in quarter beats) to Tone's
 *  Bars:Beats:Sixteenths string, given the bar length. */
function beatsToBarsBeats(beat, beatsPerBar) {
  const bar = Math.floor(beat / beatsPerBar);
  const beatInBar = Math.floor(beat % beatsPerBar);
  const sixteenths = (beat - Math.floor(beat)) * 4;
  return `${bar}:${beatInBar}:${sixteenths}`;
}

export class Scheduler {
  constructor(Tone, osmd, player) {
    this.Tone = Tone;
    this.osmd = osmd;
    this.player = player;
    this.piece = null;
    this.part = null;
    this.state = "stopped"; // 'stopped' | 'playing' | 'paused'
    this.onStep = null; // optional callback(event) when the cursor lands on a note
    this.onEnd = null; // optional callback() when playback reaches the end
  }

  /** Load a piece's parsed JSON (events, beatsPerBar, tempo). */
  setPiece(piece) {
    this.stop();
    this.piece = piece;
    const Tone = this.Tone;
    Tone.getTransport().timeSignature = piece.beatsPerBar;
    Tone.getTransport().bpm.value = piece.tempo;
  }

  setBpm(bpm) {
    this.Tone.getTransport().bpm.value = bpm;
  }

  _buildPart() {
    const Tone = this.Tone;
    const { events, beatsPerBar } = this.piece;

    // End of piece = latest note-off across all events.
    const endBeat = events.reduce((max, ev) => {
      const dur = ev.notes.reduce((d, n) => Math.max(d, n.durBeats), 0);
      return Math.max(max, ev.beat + dur);
    }, 0);

    this.part = new Tone.Part((time, ev) => {
      if (!ev.rest) {
        const bpm = Tone.getTransport().bpm.value;
        for (const n of ev.notes) {
          this.player.triggerNote(n.midi, n.durBeats * (60 / bpm), time);
        }
      }
      // Visual updates happen on the draw thread, aligned to the audio time.
      Tone.getDraw().schedule(() => this._advanceCursor(ev), time);
    }, events.map((ev) => [beatsToBarsBeats(ev.beat, beatsPerBar), ev]));

    this.part.start(0);

    // Schedule an end-of-piece callback one beat after the final note.
    this._endId = Tone.getTransport().scheduleOnce((time) => {
      Tone.getDraw().schedule(() => this._handleEnd(), time);
    }, beatsToBarsBeats(endBeat, beatsPerBar));
  }

  _advanceCursor(ev) {
    // The cursor starts on step 0 (set in play()); advance once per later event
    // so the highlight tracks the currently sounding note.
    if (ev.step > 0) this.osmd.cursor.next();
    this._scrollCursorIntoView();
    if (this.onStep) this.onStep(ev);
  }

  _scrollCursorIntoView() {
    const el = this.osmd.cursor && this.osmd.cursor.cursorElement;
    if (!el || !el.getBoundingClientRect) return;
    const r = el.getBoundingClientRect();
    const margin = 80;
    if (r.top < margin || r.bottom > window.innerHeight - margin) {
      el.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }

  _handleEnd() {
    if (this.state !== "playing") return;
    this.stop();
    if (this.onEnd) this.onEnd();
  }

  play() {
    const Tone = this.Tone;
    if (this.state === "paused") {
      Tone.getTransport().start();
      this.state = "playing";
      return;
    }
    // start from a clean stopped state
    Tone.getTransport().stop();
    Tone.getTransport().position = 0;
    this._disposePart();
    this.osmd.cursor.reset();
    this.osmd.cursor.show();
    this._buildPart();
    this.player.startMetronome(this.piece.beatsPerBar);
    Tone.getTransport().start();
    this.state = "playing";
  }

  pause() {
    if (this.state !== "playing") return;
    this.Tone.getTransport().pause();
    this.state = "paused";
  }

  stop() {
    const Tone = this.Tone;
    Tone.getTransport().stop();
    Tone.getTransport().position = 0;
    this._disposePart();
    this.player.stopMetronome();
    if (this.osmd && this.osmd.cursor) {
      this.osmd.cursor.reset();
      this.osmd.cursor.hide();
    }
    this.state = "stopped";
  }

  _disposePart() {
    if (this.part) {
      this.part.dispose();
      this.part = null;
    }
    if (this._endId != null) {
      this.Tone.getTransport().clear(this._endId);
      this._endId = null;
    }
  }
}

export { beatsToBarsBeats };
