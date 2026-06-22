// Optional reading aid: draws the note-name letter (A-G, with accidental) above
// each notehead. Letters come from the piece JSON (authoritative); positions come
// from OSMD's graphical notes, matched by cursor step index.
//
// Positions are recomputed whenever the score re-renders (resize / rotate), since
// OSMD rebuilds its SVG each time.

function formatName(name) {
  // "F#4" -> "F#", "B-4" (music21 flat) -> "B♭", "B4" -> "B"
  const m = /^([A-G])([#\-]?)/.exec(name || "");
  if (!m) return name || "";
  const acc = m[2] === "#" ? "♯" : m[2] === "-" ? "♭" : "";
  return m[1] + acc;
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

    cursor.reset();
    let i = 0;
    while (i < this.events.length) {
      const it = cursor.iterator;
      if (!it || it.EndReached) break;
      const ev = this.events[i];
      if (ev && !ev.rest && ev.label) {
        const pos = this._noteScreenPos(cursor);
        if (pos) {
          const span = document.createElement("span");
          span.textContent = formatName(ev.label);
          span.style.left = `${pos.x - wrapRect.left}px`;
          span.style.top = `${pos.y - wrapRect.top - 18}px`;
          this.layer.appendChild(span);
        }
      }
      cursor.next();
      i++;
    }
    cursor.reset();
    if (!wasShown && cursor.hide) cursor.hide();
  }

  /** Screen position (viewport coords) of the notehead under the cursor. */
  _noteScreenPos(cursor) {
    let gnotes = [];
    try {
      gnotes = cursor.GNotesUnderCursor ? cursor.GNotesUnderCursor() : [];
    } catch (e) {
      gnotes = [];
    }
    const gnote = gnotes && gnotes[0];
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

export { formatName };
