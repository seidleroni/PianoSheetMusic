"""Authoring tool for the PianoSheetMusic web app.

Encodes melodies (and optional left-hand accompaniment) with music21 and exports,
for each piece and each left-hand mode, a pair of files:
  * docs/pieces/<id>[.notes|.triads].musicxml  -- notation, rendered by OSMD
  * docs/pieces/<id>[.notes|.triads].json      -- note events for audio + cursor

Left-hand modes:
  off     -- right-hand melody only            -> <id>.json
  notes   -- melody + single bass root notes   -> <id>.notes.json
  triads  -- melody + left-hand triads (chords) -> <id>.triads.json

It also writes docs/pieces/manifest.json listing the available pieces.

Run from the tools/ directory:   uv run build_pieces.py

Durations are quarterLengths: quarter=1, half=2, dotted-quarter=1.5, eighth=0.5.
Pitches are scientific names (e.g. 'B4', 'F#4'); the key signature handles display.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from music21 import chord, clef, key, metadata, meter, note, stream, tempo

# ---------------------------------------------------------------------------
# Right-hand melodies
# ---------------------------------------------------------------------------

# Ode to Joy (Beethoven) -- main theme, two phrases, 4/4, C major (the standard
# beginner version: all white keys).
ODE_TO_JOY = [
    ("E4", 1), ("E4", 1), ("F4", 1), ("G4", 1),
    ("G4", 1), ("F4", 1), ("E4", 1), ("D4", 1),
    ("C4", 1), ("C4", 1), ("D4", 1), ("E4", 1),
    ("E4", 1.5), ("D4", 0.5), ("D4", 2),
    ("E4", 1), ("E4", 1), ("F4", 1), ("G4", 1),
    ("G4", 1), ("F4", 1), ("E4", 1), ("D4", 1),
    ("C4", 1), ("C4", 1), ("D4", 1), ("E4", 1),
    ("D4", 1.5), ("C4", 0.5), ("C4", 2),
]

# Happy Birthday (public domain) -- 3/4, G major. Bars cleanly without a pickup.
HAPPY_BIRTHDAY = [
    ("D4", 0.5), ("D4", 0.5), ("E4", 1), ("D4", 1), ("G4", 1), ("F#4", 2),
    ("D4", 0.5), ("D4", 0.5), ("E4", 1), ("D4", 1), ("A4", 1), ("G4", 2),
    ("D4", 0.5), ("D4", 0.5), ("D5", 1), ("B4", 1), ("G4", 1), ("F#4", 2),
    ("C5", 0.5), ("C5", 0.5), ("B4", 1), ("G4", 1), ("A4", 1), ("G4", 2),
]

# ---------------------------------------------------------------------------
# Left-hand chords (one per measure). root = single bass note ("notes" mode);
# triad = the three chord tones ("triads" mode). Voiced in the bass clef range.
# ---------------------------------------------------------------------------

CHORDS = {
    "C": {"root": "C3", "triad": ["C3", "E3", "G3"]},
    "G": {"root": "G2", "triad": ["G2", "B2", "D3"]},
    "D": {"root": "D3", "triad": ["D3", "F#3", "A3"]},
}

PIECES = [
    {
        "id": "ode_to_joy",
        "title": "Ode to Joy",
        "key": "C",
        "time_signature": "4/4",
        "tempo": 100,
        "melody": ODE_TO_JOY,
        "chords": ["C", "G", "C", "G", "C", "G", "C", "C"],
    },
    {
        "id": "happy_birthday",
        "title": "Happy Birthday",
        "key": "G",
        "time_signature": "3/4",
        "tempo": 100,
        "melody": HAPPY_BIRTHDAY,
        "chords": ["G", "D", "D", "G", "G", "G", "C", "G"],
    },
]

LH_MODES = ["off", "notes", "triads"]

OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "pieces"


def build_score(piece: dict, lh_mode: str) -> stream.Score:
    """Build a music21 Score: treble melody, plus an optional bass-clef left hand."""
    beats_per_bar = int(piece["time_signature"].split("/")[0])
    score = stream.Score()

    # Right hand (treble melody)
    rh = stream.Part()
    rh.append(clef.TrebleClef())
    rh.append(key.Key(piece["key"]))
    rh.append(meter.TimeSignature(piece["time_signature"]))
    rh.append(tempo.MetronomeMark(number=piece["tempo"]))
    for name, ql in piece["melody"]:
        rh.append(note.Note(name, quarterLength=ql))
    score.insert(0, rh)

    # Left hand (bass clef), one chord/note per measure
    if lh_mode in ("notes", "triads"):
        lh = stream.Part()
        lh.append(clef.BassClef())
        lh.append(key.Key(piece["key"]))
        lh.append(meter.TimeSignature(piece["time_signature"]))
        for chord_name in piece["chords"]:
            spec = CHORDS[chord_name]
            if lh_mode == "notes":
                lh.append(note.Note(spec["root"], quarterLength=beats_per_bar))
            else:
                lh.append(chord.Chord(spec["triad"], quarterLength=beats_per_bar))
        score.insert(0, lh)

    md = metadata.Metadata(title=piece["title"])
    md.movementName = f"{piece['key']} Major"  # shown as a subtitle on the score
    score.metadata = md
    return score


def score_to_events(score: stream.Score) -> list[dict]:
    """Flatten a score into onset-grouped events.

    One event per distinct onset (timestamp), holding every note that starts
    there across both hands. This matches how the OSMD cursor steps through the
    score (one step per vertical slice), keeping audio and cursor aligned.
    `beat` and `durBeats` are in quarter-note units (= beats for x/4 meters).
    """
    groups: dict[float, list] = defaultdict(list)
    for el in score.flatten().notesAndRests:
        groups[round(float(el.offset), 4)].append(el)

    events = []
    for step, beat in enumerate(sorted(groups)):
        notes = []
        for el in groups[beat]:
            dur = round(float(el.quarterLength), 4)
            if el.isRest:
                continue
            if isinstance(el, chord.Chord):
                for p in el.pitches:
                    notes.append({"midi": p.midi, "durBeats": dur, "name": p.nameWithOctave})
            else:
                notes.append({"midi": el.pitch.midi, "durBeats": dur, "name": el.nameWithOctave})
        # Label the melody (highest-sounding note) for the note-name overlay.
        label = max(notes, key=lambda n: n["midi"])["name"] if notes else None
        events.append({
            "step": step,
            "beat": beat,
            "rest": len(notes) == 0,
            "notes": notes,
            "label": label,
        })
    return events


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []

    for piece in PIECES:
        beats_per_bar = int(piece["time_signature"].split("/")[0])
        for lh_mode in LH_MODES:
            score = build_score(piece, lh_mode)
            suffix = "" if lh_mode == "off" else f".{lh_mode}"
            stem = f"{piece['id']}{suffix}"

            score.write("musicxml", fp=str(OUT_DIR / f"{stem}.musicxml"))
            data = {
                "id": piece["id"],
                "title": piece["title"],
                "key": f"{piece['key']} Major",
                "timeSignature": piece["time_signature"],
                "beatsPerBar": beats_per_bar,
                "tempo": piece["tempo"],
                "leftHand": lh_mode,
                "clefs": ["treble"] if lh_mode == "off" else ["treble", "bass"],
                "events": score_to_events(score),
            }
            (OUT_DIR / f"{stem}.json").write_text(
                json.dumps(data, indent=2), encoding="utf-8"
            )
            print(f"  wrote {stem}.musicxml/json ({len(data['events'])} events)")

        manifest.append(
            {"id": piece["id"], "title": piece["title"], "tempo": piece["tempo"]}
        )

    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"  wrote manifest.json ({len(manifest)} pieces)")
    print("Done.")


if __name__ == "__main__":
    main()
