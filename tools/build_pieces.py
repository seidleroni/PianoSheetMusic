"""Authoring tool for the PianoSheetMusic web app.

Encodes melodies with music21 and exports, for each piece:
  * docs/pieces/<id>.musicxml   -- standard notation, rendered by OpenSheetMusicDisplay
  * docs/pieces/<id>.json       -- authoritative note events (MIDI, beats, durations)
                                   used by the web app for audio + cursor scheduling

It also writes docs/pieces/manifest.json listing the available pieces.

Run from the tools/ directory:   uv run build_pieces.py

Durations are quarterLengths: quarter=1, half=2, dotted-quarter=1.5, eighth=0.5.
Pitches are scientific names (e.g. 'B4', 'F#4'); the key signature handles display.
"""

from __future__ import annotations

import json
from pathlib import Path

from music21 import chord, clef, key, metadata, meter, note, stream, tempo

# ---------------------------------------------------------------------------
# Piece definitions  (right-hand melody only, G major, for now)
# ---------------------------------------------------------------------------

# Ode to Joy (Beethoven) -- main theme, two phrases, 4/4, G major.
ODE_TO_JOY = [
    ("B4", 1), ("B4", 1), ("C5", 1), ("D5", 1),
    ("D5", 1), ("C5", 1), ("B4", 1), ("A4", 1),
    ("G4", 1), ("G4", 1), ("A4", 1), ("B4", 1),
    ("B4", 1.5), ("A4", 0.5), ("A4", 2),
    ("B4", 1), ("B4", 1), ("C5", 1), ("D5", 1),
    ("D5", 1), ("C5", 1), ("B4", 1), ("A4", 1),
    ("G4", 1), ("G4", 1), ("A4", 1), ("B4", 1),
    ("A4", 1.5), ("G4", 0.5), ("G4", 2),
]

# Happy Birthday (public domain) -- 3/4, G major. Bars cleanly without a pickup
# (starts on beat 1), which keeps the notation clean for a beginner reader.
HAPPY_BIRTHDAY = [
    ("D4", 0.5), ("D4", 0.5), ("E4", 1), ("D4", 1), ("G4", 1), ("F#4", 2),
    ("D4", 0.5), ("D4", 0.5), ("E4", 1), ("D4", 1), ("A4", 1), ("G4", 2),
    ("D4", 0.5), ("D4", 0.5), ("D5", 1), ("B4", 1), ("G4", 1), ("F#4", 2),
    ("C5", 0.5), ("C5", 0.5), ("B4", 1), ("G4", 1), ("A4", 1), ("G4", 2),
]

PIECES = [
    {
        "id": "ode_to_joy",
        "title": "Ode to Joy",
        "time_signature": "4/4",
        "tempo": 100,
        "melody": ODE_TO_JOY,
    },
    {
        "id": "happy_birthday",
        "title": "Happy Birthday",
        "time_signature": "3/4",
        "tempo": 100,
        "melody": HAPPY_BIRTHDAY,
    },
]

# ---------------------------------------------------------------------------
# Build helpers
# ---------------------------------------------------------------------------

OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "pieces"


def build_score(piece: dict) -> stream.Score:
    """Turn a piece definition into a music21 Score (single treble part)."""
    score = stream.Score()
    part = stream.Part()
    part.append(clef.TrebleClef())
    part.append(key.Key("G"))
    part.append(meter.TimeSignature(piece["time_signature"]))
    part.append(tempo.MetronomeMark(number=piece["tempo"]))
    for name, ql in piece["melody"]:
        part.append(note.Note(name, quarterLength=ql))
    score.insert(0, part)
    score.metadata = metadata.Metadata(title=piece["title"])
    return score


def score_to_events(score: stream.Score) -> list[dict]:
    """Flatten a score into ordered note/rest events with global beat positions.

    `offset` and `quarterLength` are in quarter-note units, which equal beats
    for x/4 time signatures -- matching the web app's scheduler.
    """
    events = []
    flat = score.flatten().notesAndRests
    for step, el in enumerate(flat):
        ev = {
            "step": step,
            "beat": round(float(el.offset), 4),
            "durBeats": round(float(el.quarterLength), 4),
        }
        if isinstance(el, note.Rest):
            ev.update(rest=True, midis=[], names=[])
        elif isinstance(el, chord.Chord):
            ev.update(
                rest=False,
                midis=[p.midi for p in el.pitches],
                names=[p.nameWithOctave for p in el.pitches],
            )
        else:  # note.Note
            ev.update(rest=False, midis=[el.pitch.midi], names=[el.nameWithOctave])
        events.append(ev)
    return events


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []

    for piece in PIECES:
        score = build_score(piece)

        xml_path = OUT_DIR / f"{piece['id']}.musicxml"
        score.write("musicxml", fp=str(xml_path))

        beats_per_bar = int(piece["time_signature"].split("/")[0])
        data = {
            "id": piece["id"],
            "title": piece["title"],
            "timeSignature": piece["time_signature"],
            "beatsPerBar": beats_per_bar,
            "tempo": piece["tempo"],
            "events": score_to_events(score),
        }
        json_path = OUT_DIR / f"{piece['id']}.json"
        json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        manifest.append(
            {"id": piece["id"], "title": piece["title"], "tempo": piece["tempo"]}
        )
        print(f"  wrote {xml_path.name} and {json_path.name} "
              f"({len(data['events'])} events)")

    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"  wrote manifest.json ({len(manifest)} pieces)")
    print("Done.")


if __name__ == "__main__":
    main()
