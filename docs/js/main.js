// App entry point. Loads Tone.js (ESM), uses the OSMD UMD global, and wires the
// piece picker, transport controls, tempo slider, metronome, and note labels.

import * as Tone from "https://cdn.jsdelivr.net/npm/tone@15/+esm";
import { Player } from "./player.js";
import { Scheduler } from "./scheduler.js";
import { NoteLabels } from "./notelabels.js";
import { StaffGuide } from "./staffguide.js";

const OSMD = window.opensheetmusicdisplay;

// --- DOM ---
const els = {
  piece: document.getElementById("piece"),
  play: document.getElementById("play"),
  pause: document.getElementById("pause"),
  stop: document.getElementById("stop"),
  tempo: document.getElementById("tempo"),
  bpm: document.getElementById("bpm"),
  metronome: document.getElementById("metronome"),
  labels: document.getElementById("labels"),
  guide: document.getElementById("guide"),
  status: document.getElementById("status"),
  wrapper: document.getElementById("osmd-wrapper"),
  osmd: document.getElementById("osmd"),
  noteLabels: document.getElementById("note-labels"),
  staffGuide: document.getElementById("staff-guide"),
};

function setStatus(msg) {
  els.status.textContent = msg || "";
}

// --- OSMD ---
const osmd = new OSMD.OpenSheetMusicDisplay(els.osmd, {
  autoResize: false, // handled manually so labels can be rebuilt after render
  backend: "svg",
  drawTitle: true,
  drawSubtitle: true, // shows the key (e.g. "C Major") under the title
  drawComposer: false,
  drawLyricist: false,
  drawCredits: false,
  drawPartNames: false,
});

function computeZoom() {
  const w = els.wrapper.clientWidth || window.innerWidth;
  return Math.max(0.55, Math.min(1.0, w / 700));
}

// --- engine ---
const player = new Player(Tone);
const scheduler = new Scheduler(Tone, osmd, player);
const noteLabels = new NoteLabels(osmd, els.wrapper, els.noteLabels);
const staffGuide = new StaffGuide(els.staffGuide);

let labelsOn = true; // note-name letters on by default (helps beginners read)
let soundsLoaded = false;

scheduler.onEnd = () => updateButtons();

// --- piece loading ---
async function loadManifest() {
  const res = await fetch("./pieces/manifest.json");
  const pieces = await res.json();
  els.piece.innerHTML = "";
  for (const p of pieces) {
    const opt = document.createElement("option");
    opt.value = p.id;
    opt.textContent = p.title;
    els.piece.appendChild(opt);
  }
  return pieces;
}

async function loadPiece(id) {
  scheduler.stop();
  updateButtons();
  setStatus("Loading sheet music…");
  try {
    const [xml, data] = await Promise.all([
      fetch(`./pieces/${id}.musicxml`).then((r) => r.text()),
      fetch(`./pieces/${id}.json`).then((r) => r.json()),
    ]);
    await osmd.load(xml);
    osmd.zoom = computeZoom();
    osmd.render();
    scheduler.setPiece(data);
    noteLabels.setEvents(data.events);
    noteLabels.setVisible(labelsOn);
    staffGuide.setKey(data.key);
    els.tempo.value = data.tempo;
    els.bpm.textContent = data.tempo;
    setStatus("");
  } catch (err) {
    console.error(err);
    setStatus("Could not load this piece.");
  }
}

// --- transport buttons ---
async function onPlay() {
  // First user gesture: start the audio context and load samples once.
  await Tone.start();
  if (!soundsLoaded) {
    setStatus("Loading piano sounds…");
    await player.load();
    soundsLoaded = true;
    setStatus("");
  }
  scheduler.play();
  updateButtons();
}

function onPause() {
  scheduler.pause();
  updateButtons();
}

function onStop() {
  scheduler.stop();
  updateButtons();
}

function updateButtons() {
  const s = scheduler.state;
  els.play.disabled = s === "playing";
  els.pause.disabled = s !== "playing";
  els.stop.disabled = s === "stopped";
  els.play.textContent = s === "paused" ? "▶ Resume" : "▶ Play";
}

// --- toggles & tempo ---
function onTempo() {
  const v = Number(els.tempo.value);
  els.bpm.textContent = v;
  scheduler.setBpm(v);
}

function toggleMetronome() {
  const on = els.metronome.getAttribute("aria-pressed") !== "true";
  els.metronome.setAttribute("aria-pressed", String(on));
  player.setMetronomeEnabled(on);
}

function toggleLabels() {
  labelsOn = els.labels.getAttribute("aria-pressed") !== "true";
  els.labels.setAttribute("aria-pressed", String(labelsOn));
  noteLabels.setVisible(labelsOn);
}

function toggleGuide() {
  const on = els.guide.getAttribute("aria-pressed") !== "true";
  els.guide.setAttribute("aria-pressed", String(on));
  staffGuide.setVisible(on);
}

// --- resize (re-render + reposition labels), only when not playing ---
let resizeTimer = null;
function onResize() {
  if (scheduler.state === "playing") return;
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (!osmd.GraphicSheet && !osmd.graphic) return; // nothing loaded yet
    osmd.zoom = computeZoom();
    osmd.render();
    noteLabels.setVisible(labelsOn);
  }, 150);
}

// --- init ---
async function init() {
  els.play.addEventListener("click", onPlay);
  els.pause.addEventListener("click", onPause);
  els.stop.addEventListener("click", onStop);
  els.tempo.addEventListener("input", onTempo);
  els.metronome.addEventListener("click", toggleMetronome);
  els.labels.addEventListener("click", toggleLabels);
  els.guide.addEventListener("click", toggleGuide);
  els.piece.addEventListener("change", () => loadPiece(els.piece.value));
  window.addEventListener("resize", onResize);

  try {
    const pieces = await loadManifest();
    if (pieces.length) await loadPiece(pieces[0].id);
    updateButtons();
  } catch (err) {
    console.error(err);
    setStatus("Could not load the piece list. Are you serving over http://?");
  }
}

init();
