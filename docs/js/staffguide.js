// A clean, self-drawn staff reference legend ("FACE" / "Every Good Boy Does Fine").
// Drawn at a readable size (independent of the tiny live staff) to teach which
// line/space is which note. Treble now; bass is added with the left-hand feature.

const CLEFS = {
  treble: {
    label: "Treble clef · right hand",
    // bottom -> top
    lines: ["E", "G", "B", "D", "F"],
    spaces: ["F", "A", "C", "E"],
    linesMnemonic: "Every Good Boy Does Fine",
    spacesMnemonic: "spell FACE",
  },
  bass: {
    label: "Bass clef · left hand",
    lines: ["G", "B", "D", "F", "A"],
    spaces: ["A", "C", "E", "G"],
    linesMnemonic: "Good Boys Do Fine Always",
    spacesMnemonic: "All Cows Eat Grass",
  },
};

function staffSvg(clef) {
  const c = CLEFS[clef];
  const gap = 18; // line spacing (readable)
  const top = 14;
  const left = 70;
  const right = 150;
  const yLine = (i) => top + (4 - i) * gap; // i=0 bottom line .. 4 top line
  let parts = [];
  // staff lines
  for (let i = 0; i < 5; i++) {
    const y = yLine(i);
    parts.push(`<line x1="${left}" y1="${y}" x2="${right}" y2="${y}" stroke="#374151" stroke-width="1"/>`);
    // line letter (left side)
    parts.push(
      `<text x="${left - 16}" y="${y + 4}" class="sg-line">${c.lines[i]}</text>`,
    );
  }
  // space letters (between lines)
  for (let i = 0; i < 4; i++) {
    const y = (yLine(i) + yLine(i + 1)) / 2;
    parts.push(
      `<text x="${right + 8}" y="${y + 4}" class="sg-space">${c.spaces[i]}</text>`,
    );
  }
  // clef hint
  parts.push(
    `<text x="${left - 52}" y="${top + 3.0 * gap}" class="sg-clef">${clef === "treble" ? "𝄞" : "𝄢"}</text>`,
  );
  return `<svg viewBox="0 0 220 ${top * 2 + gap * 4}" width="220" class="sg-staff" role="img" aria-label="${c.label}">${parts.join("")}</svg>`;
}

export class StaffGuide {
  constructor(container) {
    this.el = container;
    this.visible = true;
    this.clefs = ["treble"]; // becomes ["treble","bass"] when left hand is on
    this.keyName = "";
  }

  setVisible(on) {
    this.visible = on;
    this.el.style.display = on ? "block" : "none";
    if (on) this.render();
  }

  setClefs(clefs) {
    this.clefs = clefs;
    if (this.visible) this.render();
  }

  setKey(keyName) {
    this.keyName = keyName || "";
    if (this.visible) this.render();
  }

  render() {
    const blocks = this.clefs
      .map((clef) => {
        const c = CLEFS[clef];
        return `<div class="sg-block">
          ${staffSvg(clef)}
          <div class="sg-text">
            <div class="sg-cleflabel">${c.label}</div>
            <div><b class="sg-line">Lines</b> (bottom→top): ${c.lines.join(" ")} — <i>${c.linesMnemonic}</i></div>
            <div><b class="sg-space">Spaces</b> (bottom→top): ${c.spaces.join(" ")} — <i>${c.spacesMnemonic}</i></div>
          </div>
        </div>`;
      })
      .join("");
    const heading = this.keyName
      ? `<div class="sg-heading">Reading guide — Key of ${this.keyName}</div>`
      : `<div class="sg-heading">Reading guide</div>`;
    this.el.innerHTML = heading + blocks;
  }
}
