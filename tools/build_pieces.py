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
A pitch of None is a rest (a breath in the melody).
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from music21 import chord, clef, key, metadata, meter, note, stream, tempo

# ---------------------------------------------------------------------------
# Right-hand melodies
# ---------------------------------------------------------------------------

# Ode to Joy (Beethoven) -- the complete 16-bar theme (A A' B A'), 4/4, C major
# (the standard beginner version: all white keys). The B section ("re re mi do")
# dips to G3 at its close before the main phrase returns.
ODE_TO_JOY = [
    ("E4", 1), ("E4", 1), ("F4", 1), ("G4", 1),                     # A
    ("G4", 1), ("F4", 1), ("E4", 1), ("D4", 1),
    ("C4", 1), ("C4", 1), ("D4", 1), ("E4", 1),
    ("E4", 1.5), ("D4", 0.5), ("D4", 2),
    ("E4", 1), ("E4", 1), ("F4", 1), ("G4", 1),                     # A'
    ("G4", 1), ("F4", 1), ("E4", 1), ("D4", 1),
    ("C4", 1), ("C4", 1), ("D4", 1), ("E4", 1),
    ("D4", 1.5), ("C4", 0.5), ("C4", 2),
    ("D4", 1), ("D4", 1), ("E4", 1), ("C4", 1),                     # B
    ("D4", 1), ("E4", 0.5), ("F4", 0.5), ("E4", 1), ("C4", 1),
    ("D4", 1), ("E4", 0.5), ("F4", 0.5), ("E4", 1), ("D4", 1),
    ("C4", 1), ("D4", 1), ("G3", 2),
    ("E4", 1), ("E4", 1), ("F4", 1), ("G4", 1),                     # A'
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

# Twinkle, Twinkle, Little Star (public domain) -- 4/4, C major. All white keys.
TWINKLE = [
    ("C4", 1), ("C4", 1), ("G4", 1), ("G4", 1),
    ("A4", 1), ("A4", 1), ("G4", 2),
    ("F4", 1), ("F4", 1), ("E4", 1), ("E4", 1),
    ("D4", 1), ("D4", 1), ("C4", 2),
    ("G4", 1), ("G4", 1), ("F4", 1), ("F4", 1),
    ("E4", 1), ("E4", 1), ("D4", 2),
    ("G4", 1), ("G4", 1), ("F4", 1), ("F4", 1),
    ("E4", 1), ("E4", 1), ("D4", 2),
    ("C4", 1), ("C4", 1), ("G4", 1), ("G4", 1),
    ("A4", 1), ("A4", 1), ("G4", 2),
    ("F4", 1), ("F4", 1), ("E4", 1), ("E4", 1),
    ("D4", 1), ("D4", 1), ("C4", 2),
]

# Mary Had a Little Lamb (public domain) -- 4/4, C major. All white keys.
MARY = [
    ("E4", 1), ("D4", 1), ("C4", 1), ("D4", 1),
    ("E4", 1), ("E4", 1), ("E4", 2),
    ("D4", 1), ("D4", 1), ("D4", 2),
    ("E4", 1), ("G4", 1), ("G4", 2),
    ("E4", 1), ("D4", 1), ("C4", 1), ("D4", 1),
    ("E4", 1), ("E4", 1), ("E4", 1), ("E4", 1),
    ("D4", 1), ("D4", 1), ("E4", 1), ("D4", 1),
    ("C4", 4),
]

# Frere Jacques (public domain) -- 4/4, C major. A tonic-drone round; the closing
# "din dan don" dips to G3 (just below the treble staff).
FRERE_JACQUES = [
    ("C4", 1), ("D4", 1), ("E4", 1), ("C4", 1),
    ("C4", 1), ("D4", 1), ("E4", 1), ("C4", 1),
    ("E4", 1), ("F4", 1), ("G4", 2),
    ("E4", 1), ("F4", 1), ("G4", 2),
    ("G4", 0.5), ("A4", 0.5), ("G4", 0.5), ("F4", 0.5), ("E4", 1), ("C4", 1),
    ("G4", 0.5), ("A4", 0.5), ("G4", 0.5), ("F4", 0.5), ("E4", 1), ("C4", 1),
    ("C4", 1), ("G3", 1), ("C4", 2),
    ("C4", 1), ("G3", 1), ("C4", 2),
]

# Old MacDonald Had a Farm (public domain) -- one full verse with the "moo moo"
# strain, 4/4, C major. "Old Mac-Don-ald" dips below the staff (C4 C4 C4 G3),
# and the "and" / "with a" upbeats follow a breath rest inside each "O" bar.
OLD_MACDONALD = [
    ("C4", 1), ("C4", 1), ("C4", 1), ("G3", 1),                     # Old Mac-Don-ald
    ("A3", 1), ("A3", 1), ("G3", 2),                                # had a farm
    ("E4", 1), ("E4", 1), ("D4", 1), ("D4", 1),                     # E-I-E-I
    ("C4", 2), (None, 1), ("G3", 1),                                # O -- and
    ("C4", 1), ("C4", 1), ("C4", 1), ("G3", 1),                     # on that farm he
    ("A3", 1), ("A3", 1), ("G3", 2),                                # had a cow
    ("E4", 1), ("E4", 1), ("D4", 1), ("D4", 1),                     # E-I-E-I
    ("C4", 2), (None, 1), ("G3", 0.5), ("G3", 0.5),                 # O -- with a
    ("C4", 1), ("C4", 1), ("C4", 1), ("G3", 0.5), ("G3", 0.5),      # moo moo here, and a
    ("C4", 1), ("C4", 1), ("C4", 2),                                # moo moo there
    ("C4", 0.5), ("C4", 0.5), ("C4", 1),                            # here a moo,
    ("C4", 0.5), ("C4", 0.5), ("C4", 1),                            # there a moo,
    ("C4", 0.5), ("C4", 0.5), ("C4", 0.5), ("C4", 0.5),             # ev-ry-where a
    ("C4", 1), ("C4", 1),                                           # moo moo
    ("C4", 1), ("C4", 1), ("C4", 1), ("G3", 1),                     # Old Mac-Don-ald
    ("A3", 1), ("A3", 1), ("G3", 2),                                # had a farm
    ("E4", 1), ("E4", 1), ("D4", 1), ("D4", 1),                     # E-I-E-I
    ("C4", 4),                                                      # O!
]

# Fur Elise (Beethoven, WoO 59) -- the famous A-section theme, A minor.
# Beethoven wrote it in 3/8 with sixteenth notes; this is the common beginner
# transcription in 3/4 with eighth notes (same pitches, easier to read). It opens
# with a one-beat pickup (the iconic E-D#), and the short rests after each long
# note are absorbed into that note's duration so playback stays gap-aligned.
# Accidentals (D#, G#) are spelled explicitly; the A-minor key signature is blank.
FUR_ELISE = [
    ("E5", 0.5), ("D#5", 0.5),                                    # pickup (1 beat)
    ("E5", 0.5), ("D#5", 0.5), ("E5", 0.5), ("B4", 0.5), ("D5", 0.5), ("C5", 0.5),
    ("A4", 1.5), ("C4", 0.5), ("E4", 0.5), ("A4", 0.5),           # i  (A minor)
    ("B4", 1.5), ("E4", 0.5), ("G#4", 0.5), ("B4", 0.5),          # V  (E major)
    ("C5", 1.5), ("E4", 0.5), ("E5", 0.5), ("D#5", 0.5),          # i, lead back
    ("E5", 0.5), ("D#5", 0.5), ("E5", 0.5), ("B4", 0.5), ("D5", 0.5), ("C5", 0.5),
    ("A4", 1.5), ("C4", 0.5), ("E4", 0.5), ("A4", 0.5),           # i
    ("B4", 1.5), ("E4", 0.5), ("C5", 0.5), ("B4", 0.5),           # V -> cadence
    ("A4", 3.0),                                                  # resolution
]

# Jingle Bells (James Lord Pierpont, public domain) -- the chorus, 4/4, C major.
# First time through, "sleigh" ends with the shouted "hey!" on G; the second
# ending walks down G-G-F-D and lands on C.
JINGLE_BELLS = [
    ("E4", 1), ("E4", 1), ("E4", 2),                                # jin-gle bells
    ("E4", 1), ("E4", 1), ("E4", 2),                                # jin-gle bells
    ("E4", 1), ("G4", 1), ("C4", 1.5), ("D4", 0.5),                 # jin-gle all the
    ("E4", 4),                                                      # way
    ("F4", 1), ("F4", 1), ("F4", 1.5), ("F4", 0.5),                 # oh what fun it
    ("F4", 1), ("E4", 1), ("E4", 1), ("E4", 0.5), ("E4", 0.5),      # is to ride in a
    ("E4", 1), ("D4", 1), ("D4", 1), ("E4", 1),                     # one-horse o-pen
    ("D4", 2), ("G4", 2),                                           # sleigh -- hey!
    ("E4", 1), ("E4", 1), ("E4", 2),
    ("E4", 1), ("E4", 1), ("E4", 2),
    ("E4", 1), ("G4", 1), ("C4", 1.5), ("D4", 0.5),
    ("E4", 4),
    ("F4", 1), ("F4", 1), ("F4", 1.5), ("F4", 0.5),
    ("F4", 1), ("E4", 1), ("E4", 1), ("E4", 0.5), ("E4", 0.5),
    ("G4", 1), ("G4", 1), ("F4", 1), ("D4", 1),                     # one-horse o-pen
    ("C4", 4),                                                      # sleigh
]

# When the Saints Go Marching In (public domain) -- 4/4, C major. Opens with a
# three-beat pickup ("Oh when the saints"); each later entry of that figure
# starts after a one-beat rest, as sung.
WHEN_THE_SAINTS = [
    ("C4", 1), ("E4", 1), ("F4", 1),                  # pickup (3 beats): oh when the
    ("G4", 4),                                        # saints
    (None, 1), ("C4", 1), ("E4", 1), ("F4", 1),       # -- oh when the
    ("G4", 4),                                        # saints
    (None, 1), ("C4", 1), ("E4", 1), ("F4", 1),       # -- oh when the
    ("G4", 2), ("E4", 2),                             # saints go
    ("C4", 2), ("E4", 2),                             # march-ing
    ("D4", 4),                                        # in
    (None, 1), ("E4", 1), ("E4", 1), ("D4", 1),       # -- oh how I
    ("C4", 2), ("C4", 1), ("E4", 1),                  # want -- to be
    ("G4", 2), ("G4", 1), ("G4", 1),                  # in that num-
    ("F4", 2), ("E4", 1), ("F4", 1),                  # -ber, when the
    ("G4", 2), ("E4", 2),                             # saints go
    ("C4", 2), ("D4", 2),                             # march-ing
    ("C4", 4),                                        # in
]

# Amazing Grace ("New Britain", public domain) -- 3/4, G major, fully pentatonic
# (G A B D E only). One-beat pickup ("A-"); the long "me" gets a two-beat breath
# before the "I" upbeat, as sung. "-ing"/"a"/"but" are two-note eighth melismas.
AMAZING_GRACE = [
    ("D4", 1),                                        # pickup (1 beat): A-
    ("G4", 2), ("B4", 0.5), ("G4", 0.5),              # maz-ing
    ("B4", 2), ("A4", 1),                             # grace, how
    ("G4", 2), ("E4", 1),                             # sweet the
    ("D4", 2), ("D4", 1),                             # sound that
    ("G4", 2), ("B4", 0.5), ("G4", 0.5),              # saved a
    ("B4", 2), ("A4", 1),                             # wretch like
    ("D5", 3),                                        # me
    (None, 2), ("B4", 1),                             # -- I
    ("D5", 2), ("B4", 1),                             # once was
    ("G4", 2), ("E4", 1),                             # lost, but
    ("G4", 2), ("E4", 1),                             # now am
    ("D4", 2), ("D4", 1),                             # found, was
    ("G4", 2), ("B4", 0.5), ("G4", 0.5),              # blind but
    ("B4", 2), ("A4", 1),                             # now I
    ("G4", 3),                                        # see
]

# ---------------------------------------------------------------------------
# Left-hand chords (one per measure). root = single bass note ("notes" mode);
# triad = the three chord tones ("triads" mode). Voiced in the bass clef range.
# ---------------------------------------------------------------------------

CHORDS = {
    "C": {"root": "C3", "triad": ["C3", "E3", "G3"]},
    "F": {"root": "F2", "triad": ["F2", "A2", "C3"]},
    "G": {"root": "G2", "triad": ["G2", "B2", "D3"]},
    "D": {"root": "D3", "triad": ["D3", "F#3", "A3"]},
    "Am": {"root": "A2", "triad": ["A2", "C3", "E3"]},
    "E": {"root": "E2", "triad": ["E2", "G#2", "B2"]},
}

PIECES = [
    {
        "id": "ode_to_joy",
        "title": "Ode to Joy",
        "key": "C",
        "time_signature": "4/4",
        "tempo": 100,
        "melody": ODE_TO_JOY,
        "chords": ["C", "G", "C", "G", "C", "G", "C", "C",
                   "G", "C", "G", "G", "C", "G", "C", "C"],
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
    {
        "id": "twinkle",
        "title": "Twinkle, Twinkle, Little Star",
        "key": "C",
        "time_signature": "4/4",
        "tempo": 100,
        "melody": TWINKLE,
        "chords": ["C", "F", "F", "C", "C", "G", "C", "G", "C", "F", "F", "C"],
    },
    {
        "id": "mary_had_a_little_lamb",
        "title": "Mary Had a Little Lamb",
        "key": "C",
        "time_signature": "4/4",
        "tempo": 100,
        "melody": MARY,
        "chords": ["C", "C", "G", "C", "C", "C", "G", "C"],
    },
    {
        "id": "frere_jacques",
        "title": "Frère Jacques",
        "key": "C",
        "time_signature": "4/4",
        "tempo": 100,
        "melody": FRERE_JACQUES,
        "chords": ["C", "C", "C", "C", "C", "C", "C", "C"],
    },
    {
        "id": "old_macdonald",
        "title": "Old MacDonald Had a Farm",
        "key": "C",
        "time_signature": "4/4",
        "tempo": 110,
        "melody": OLD_MACDONALD,
        "chords": ["C", "F", "G", "C", "C", "F", "G", "C",
                   "C", "F", "C", "F", "C", "F", "G", "C"],
    },
    {
        "id": "fur_elise",
        "title": "Für Elise (theme)",
        "key": "A",
        "mode": "minor",
        "time_signature": "3/4",
        "tempo": 68,
        "pickup": 1.0,  # one-beat anacrusis (the opening E-D#)
        "melody": FUR_ELISE,
        "chords": ["E", "Am", "E", "Am", "E", "Am", "E", "Am"],
    },
    {
        "id": "jingle_bells",
        "title": "Jingle Bells",
        "key": "C",
        "time_signature": "4/4",
        "tempo": 120,
        "melody": JINGLE_BELLS,
        "chords": ["C", "C", "C", "C", "F", "C", "D", "G",
                   "C", "C", "C", "C", "F", "C", "G", "C"],
    },
    {
        "id": "when_the_saints",
        "title": "When the Saints Go Marching In",
        "key": "C",
        "time_signature": "4/4",
        "tempo": 110,
        "pickup": 3.0,  # three-beat anacrusis ("Oh when the saints")
        "melody": WHEN_THE_SAINTS,
        "chords": ["C", "C", "C", "C", "C", "C", "G", "G",
                   "C", "C", "F", "C", "G", "C"],
    },
    {
        "id": "amazing_grace",
        "title": "Amazing Grace",
        "key": "G",
        "time_signature": "3/4",
        "tempo": 84,
        "pickup": 1.0,  # one-beat anacrusis ("A-")
        "melody": AMAZING_GRACE,
        "chords": ["G", "G", "C", "G", "G", "G", "D", "D",
                   "G", "G", "C", "G", "G", "D", "G"],
    },
]

LH_MODES = ["off", "notes", "triads"]

OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "pieces"


def key_display(piece: dict) -> str:
    """Human-readable key name, e.g. 'C Major', 'A Minor' (shown as a subtitle)."""
    tonic = piece["key"].replace("-", "♭").replace("#", "♯")
    return f"{tonic} {piece.get('mode', 'major').capitalize()}"


def _piece_key(piece: dict) -> key.Key:
    return key.Key(piece["key"], piece.get("mode", "major"))


def _chunk_durations(items, measure_ql: float, pickup_ql: float):
    """Greedily split a flat list of (·, quarterLength) into per-measure lists.

    The first list fills the pickup (if any); the rest fill full measures.
    Raises if an item straddles a barline or the melody ends mid-measure, so a
    duration typo fails the build instead of silently shifting every later bar.
    """
    measures, cur, acc = [], [], 0.0
    target = pickup_ql or measure_ql
    for item in items:
        cur.append(item)
        acc += item[1]
        if acc > target + 1e-6:
            raise ValueError(
                f"item {item} straddles a barline (measure {len(measures) + 1} "
                f"sums to {acc}, expected {target})"
            )
        if acc >= target - 1e-6:
            measures.append(cur)
            cur, acc, target = [], 0.0, measure_ql
    if cur:
        raise ValueError(f"melody ends {target - acc} beats short of a full measure")
    return measures


def _validate_piece(piece: dict) -> None:
    """Check the piece's lengths: every bar must fill exactly, and the melody's
    full-measure count must match the chord list (one chord per measure)."""
    num, den = (int(x) for x in piece["time_signature"].split("/"))
    measure_ql = 4.0 * num / den
    pickup_ql = float(piece.get("pickup", 0) or 0)
    try:
        measures = _chunk_durations(piece["melody"], measure_ql, pickup_ql)
    except ValueError as e:
        raise ValueError(f"{piece['id']}: {e}") from None
    n_full = len(measures) - (1 if pickup_ql else 0)
    if n_full != len(piece["chords"]):
        raise ValueError(
            f"{piece['id']}: melody fills {n_full} measures "
            f"but 'chords' lists {len(piece['chords'])}"
        )


def build_score(piece: dict, lh_mode: str) -> stream.Score:
    """Build a music21 Score: treble melody, plus an optional bass-clef left hand."""
    ts_str = piece["time_signature"]
    num, den = (int(x) for x in ts_str.split("/"))
    measure_ql = 4.0 * num / den
    pickup_ql = float(piece.get("pickup", 0) or 0)
    score = stream.Score()

    score.insert(0, _build_melody_part(piece, lh_mode, measure_ql, pickup_ql))
    if lh_mode in ("notes", "triads"):
        score.insert(0, _build_lh_part(piece, lh_mode, measure_ql, pickup_ql))

    md = metadata.Metadata(title=piece["title"])
    md.movementName = key_display(piece)  # shown as a subtitle on the score
    score.metadata = md
    return score


def _melody_element(name: str | None, ql: float):
    """A melody note, or a rest when the pitch is None."""
    return note.Note(name, quarterLength=ql) if name else note.Rest(quarterLength=ql)


def _build_melody_part(piece, lh_mode, measure_ql, pickup_ql) -> stream.Part:
    """Treble part. Without a pickup, notes are appended flat (music21 bars them at
    write time); with a pickup, measures are built by hand so the anacrusis is a
    short, padded first measure rather than a shifted full bar."""
    rh = stream.Part()
    header = [
        clef.TrebleClef(),
        _piece_key(piece),
        meter.TimeSignature(piece["time_signature"]),
        tempo.MetronomeMark(number=piece["tempo"]),
    ]
    notes = piece["melody"]

    if not pickup_ql:
        for el in header:
            rh.append(el)
        for name, ql in notes:
            rh.append(_melody_element(name, ql))
        return rh

    for i, chunk in enumerate(_chunk_durations(notes, measure_ql, pickup_ql)):
        m = stream.Measure(number=i)  # anacrusis is measure 0, by convention
        if i == 0:
            for el in header:
                m.insert(0, el)
            m.paddingLeft = measure_ql - pickup_ql  # mark as an anacrusis
        for name, ql in chunk:
            m.append(_melody_element(name, ql))
        rh.append(m)
    return rh


def _lh_element(chord_name: str, lh_mode: str, dur: float):
    spec = CHORDS[chord_name]
    if lh_mode == "notes":
        return note.Note(spec["root"], quarterLength=dur)
    return chord.Chord(spec["triad"], quarterLength=dur)


def _build_lh_part(piece, lh_mode, measure_ql, pickup_ql) -> stream.Part:
    """Bass part: one chord/root per full measure. A pickup gets a padded rest
    measure first so both staves share the same barlines."""
    lh = stream.Part()
    header = [clef.BassClef(), _piece_key(piece), meter.TimeSignature(piece["time_signature"])]
    chords = piece["chords"]

    if not pickup_ql:
        for el in header:
            lh.append(el)
        for chord_name in chords:
            lh.append(_lh_element(chord_name, lh_mode, measure_ql))
        return lh

    anacrusis = stream.Measure(number=0)
    for el in header:
        anacrusis.insert(0, el)
    anacrusis.paddingLeft = measure_ql - pickup_ql
    anacrusis.append(note.Rest(quarterLength=pickup_ql))
    lh.append(anacrusis)
    for i, chord_name in enumerate(chords, start=1):
        m = stream.Measure(number=i)
        m.append(_lh_element(chord_name, lh_mode, measure_ql))
        lh.append(m)
    return lh


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
        _validate_piece(piece)
        beats_per_bar = int(piece["time_signature"].split("/")[0])
        for lh_mode in LH_MODES:
            score = build_score(piece, lh_mode)
            suffix = "" if lh_mode == "off" else f".{lh_mode}"
            stem = f"{piece['id']}{suffix}"

            score.write("musicxml", fp=str(OUT_DIR / f"{stem}.musicxml"))
            data = {
                "id": piece["id"],
                "title": piece["title"],
                "key": key_display(piece),
                "timeSignature": piece["time_signature"],
                "beatsPerBar": beats_per_bar,
                "tempo": piece["tempo"],
                "pickup": float(piece.get("pickup", 0) or 0),
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
