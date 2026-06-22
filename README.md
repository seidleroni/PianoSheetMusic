# PianoSheetMusic

A phone-friendly app for learning to **read sheet music** and play piano. It shows
a piece on the staff, plays it on a sampled piano with an **adjustable tempo**, and
a **follow-along cursor** highlights the note you should be playing. Optional
note-name letters (A–G) help while you learn to read.

Currently included (right-hand melody, G major): **Ode to Joy** and **Happy Birthday**.

Live site: https://seidleroni.github.io/PianoSheetMusic/

## How it works

- **`tools/`** — a Python (uv) authoring tool. `build_pieces.py` uses `music21` to
  encode each melody and export, per piece, a `.musicxml` (for display) and a `.json`
  (authoritative notes/timing used for playback). This runs **locally only**.
- **`docs/`** — the static web app served by GitHub Pages. It renders the MusicXML
  with [OpenSheetMusicDisplay](https://opensheetmusicdisplay.org/), plays it with
  [Tone.js](https://tonejs.github.io/) (sampled piano + metronome), and steps the
  cursor in time. No server needed.

## Add or edit a piece

1. Edit the piece definitions in `tools/build_pieces.py` (note name + duration in
   quarter-lengths: quarter=1, half=2, dotted-quarter=1.5, eighth=0.5).
2. Regenerate the files:
   ```sh
   cd tools
   uv run build_pieces.py
   ```
   This writes `docs/pieces/<id>.musicxml`, `docs/pieces/<id>.json`, and updates
   `docs/pieces/manifest.json`.
3. Commit and push. GitHub Pages serves the updated `docs/`.

## Preview locally (no Node required)

```sh
cd docs
python -m http.server 8000
```
Then open http://localhost:8000 . (Serving over `http://` is required — opening the
file directly will not load the modules or piece files.)

## Deploy (GitHub Pages)

Repo → **Settings → Pages → Source = "Deploy from a branch" → branch `main`,
folder `/docs`**. The site appears at the live URL above.

## Roadmap

- **Phase 2** — microphone note-checking (does the played note match the score?).
  See `docs/js/pitch.js`.
- **Phase 3** — left-hand triad accompaniment (a second part in `build_pieces.py`);
  chord-checking via a USB-MIDI keyboard (Web MIDI) rather than the microphone.
- More pieces of increasing difficulty.
