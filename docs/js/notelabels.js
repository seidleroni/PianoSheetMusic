// Optional reading aid: draws the note-name letter (A-G, with accidental) next to
// every notehead -- right-hand melody, left-hand bass notes, and each tone of a
// left-hand triad. Letters are read straight off OSMD's rendered notes, so each
// label always matches the note it sits on.
//
// Positions are recomputed whenever the score re-renders (resize / rotate), since
// OSMD rebuilds its SVG each time.

// OSMD NoteEnum -> letter (C=0, D=2, E=4, F=5, G=7, A=9, B=11).
const NOTE_LETTER = { 0: "C", 2: "D", 4: "E", 5: "F", 7: "G", 9: "A", 11: "B" };
// OSMD AccidentalEnum: SHARP=0, FLAT=1, NONE=2, NATURAL=3 (higher values are rare).
const ACCIDENTAL = { 0: "♯", 1: "♭" };

function formatName(name) {
  // "F#4" -> "F#", "B-4" (music21 flat) -> "B♭", "B4" -> "B"
  const m = /^([A-G])([#\-]?)/.exec(name || "");
  if (!m) return name || "";
  const acc = m[2] === "#" ? "♯" : m[2] === "-" ? "♭" : "";
  return m[1] + acc;
}

/** OSMD Pitch of a graphical note, or null for rests / unknowns. */
function gnotePitch(gnote) {
  try {
    const src = gnote && gnote.sourceNote;
    if (!src || (src.isRest && src.isRest())) return null;
    return src.Pitch || null;
  } catch (e) {
    return null;
  }
}

/** Letter name (no octave) of an OSMD pitch, e.g. "G", "F♯". */
function pitchName(p) {
  const letter = NOTE_LETTER[p.FundamentalNote];
  if (!letter) return "";
  return letter + (ACCIDENTAL[p.Accidental] || "");
}

export class NoteLabels {
  constructor(osmd, wrapperEl, layerEl) {
    this.osmd = osmd;
    this.wrapper = wrapperEl;
    this.layer = layerEl;
    this.events = [];
    this.visible = false;
  }

  setEvents(events) {
    this.events = events || [];
  }

  setVisible(on) {
    this.visible = on;
    this.layer.style.display = on ? "block" : "none";
    if (on) this.rebuild();
  }

  rebuild() {
    this.layer.innerHTML = "";
    if (!this.visible || !this.events.length) return;

    const cursor = this.osmd.cursor;
    if (!cursor) return;

    const wasShown = cursor.cursorElement && cursor.cursorElement.style.display !== "none";
    const wrapRect = this.wrapper.getBoundingClientRect();

    // Walk the score one vertical slice at a time (events.length == step count).
    // At each step, label every notehead that onsets there, across both staves.
    cursor.reset();
    let i = 0;
    while (i < this.events.length) {
      const it = cursor.iterator;
      if (!it || it.EndReached) break;
      this._placeStepLabels(cursor, wrapRect);
      cursor.next();
      i++;
    }
    cursor.reset();
    if (!wasShown && cursor.hide) cursor.hide();
  }

  /** Label each notehead under the cursor. A single note gets its letter above
   *  the notehead; a chord (e.g. a left-hand triad) gets a letter beside each of
   *  its noteheads so the names don't pile up on top of one another. */
  _placeStepLabels(cursor, wrapRect) {
    let gnotes = [];
    try {
      gnotes = cursor.GNotesUnderCursor ? cursor.GNotesUnderCursor() : [];
    } catch (e) {
      gnotes = [];
    }

    // Group tones by their shared notehead group. OSMD renders one VexFlow
    // stave-note per voice entry, so a single note and a whole chord (triad)
    // each map to one group element; this naturally splits treble vs bass.
    const groups = new Map();
    for (const g of gnotes) {
      const p = gnotePitch(g);
      if (!p) continue; // rest, or pitch we can't read
      const name = pitchName(p);
      if (!name) continue;
      const el = g.getSVGGElement && g.getSVGGElement();
      const half = typeof p.getHalfTone === "function" ? p.getHalfTone() : 0;
      if (!el) {
        // No rendered element: fall back to a single letter above the note.
        const pos = this._gnotePos(g);
        if (pos) this._labelAbove(name, pos.x, pos.y, wrapRect);
        continue;
      }
      if (!groups.has(el)) groups.set(el, []);
      groups.get(el).push({ name, half });
    }

    for (const [el, tones] of groups) {
      // Per-notehead boxes (the group's API box covers the whole chord, so read
      // the individual noteheads from the SVG), ordered top-to-bottom.
      const heads = Array.from(el.querySelectorAll(".vf-notehead"))
        .map((h) => h.getBoundingClientRect())
        .sort((a, b) => a.top - b.top);
      tones.sort((a, b) => b.half - a.half); // high -> low, matching head order

      if (tones.length <= 1 || heads.length <= 1) {
        // Single note: letter centered above the notehead.
        const r = heads[0];
        if (r) this._labelAbove(tones[0].name, r.left + r.width / 2, r.top, wrapRect);
        continue;
      }
      // Chord (e.g. a triad): a letter beside each notehead.
      const n = Math.min(tones.length, heads.length);
      for (let k = 0; k < n; k++) {
        const r = heads[k];
        this._labelBeside(tones[k].name, r.right, r.top + r.height / 2, wrapRect);
      }
    }
  }

  /** A letter centered horizontally above a notehead (cx = center, topY = top). */
  _labelAbove(name, cx, topY, wrapRect) {
    const span = document.createElement("span");
    span.textContent = name;
    span.style.left = `${cx - wrapRect.left}px`;
    span.style.top = `${topY - wrapRect.top - 16}px`;
    this.layer.appendChild(span);
  }

  /** A letter just to the right of a notehead, vertically centered on it. */
  _labelBeside(name, rightX, midY, wrapRect) {
    const span = document.createElement("span");
    span.textContent = name;
    span.style.left = `${rightX - wrapRect.left + 3}px`;
    span.style.top = `${midY - wrapRect.top}px`;
    span.style.transform = "translate(0, -50%)"; // anchor at left edge, centered vertically
    this.layer.appendChild(span);
  }

  /** Screen position (viewport coords) of a notehead: x = center, y = top. */
  _gnotePos(gnote) {
    if (!gnote) return null;

    // Preferred: the rendered SVG element's bounding box (handles zoom/scroll).
    try {
      const el = gnote.getSVGGElement && gnote.getSVGGElement();
      if (el && el.getBoundingClientRect) {
        const r = el.getBoundingClientRect();
        if (r.width || r.height) return { x: r.left + r.width / 2, y: r.top };
      }
    } catch (e) { /* fall through */ }

    // Fallback: compute from OSMD's internal unit coordinates (10px per unit).
    try {
      const ps = gnote.PositionAndShape;
      const zoom = this.osmd.zoom || 1;
      const unit = 10 * zoom;
      const wrapRect = this.wrapper.getBoundingClientRect();
      return {
        x: wrapRect.left + ps.AbsolutePosition.x * unit,
        y: wrapRect.top + ps.AbsolutePosition.y * unit,
      };
    } catch (e) {
      return null;
    }
  }
}

export { formatName, gnotePitch, pitchName };
