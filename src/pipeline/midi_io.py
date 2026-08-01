"""MIDI read/write utilities."""

from __future__ import annotations
from dataclasses import dataclass, field
import pretty_midi


@dataclass
class Note:
    pitch: int       # MIDI pitch (0-127)
    start: float     # start time in seconds
    end: float       # end time in seconds
    velocity: int = 64
    track: int = 0   # source track index


@dataclass
class MIDIData:
    tracks: list[list[Note]] = field(default_factory=list)
    tempo: float = 120.0
    time_signature: tuple[int, int] = (4, 4)

    @property
    def all_notes(self) -> list[Note]:
        return [n for track in self.tracks for n in track]

    @property
    def num_tracks(self) -> int:
        return len(self.tracks)


def read_midi(path: str) -> MIDIData:
    """Read a multi-track MIDI file."""
    pm = pretty_midi.PrettyMIDI(path)
    data = MIDIData()
    data.tempo = pm.estimate_tempo()
    
    for i, inst in enumerate(pm.instruments):
        if inst.is_drum:
            continue  # skip drum tracks
        track = [
            Note(
                pitch=note.pitch,
                start=note.start,
                end=note.end,
                velocity=note.velocity,
                track=i,
            )
            for note in inst.notes
        ]
        if track:
            data.tracks.append(track)
    
    return data


def write_piano_midi(
    path: str,
    melody_notes: list[Note],
    harmony_notes: list[Note] | None = None,
    tempo: float = 120.0,
) -> None:
    """Write a 2-track piano MIDI file (right hand = melody, left hand = harmony)."""
    pm = pretty_midi.PrettyMIDI(initial_tempo=tempo)
    
    # Right hand (melody) - Acoustic Grand Piano program 0
    rh = pretty_midi.Instrument(program=0, name="Right Hand")
    for n in melody_notes:
        note = pretty_midi.Note(
            velocity=n.velocity,
            pitch=n.pitch,
            start=n.start,
            end=n.end,
        )
        rh.notes.append(note)
    pm.instruments.append(rh)
    
    # Left hand (harmony) - Acoustic Grand Piano program 0
    if harmony_notes:
        lh = pretty_midi.Instrument(program=0, name="Left Hand")
        for n in harmony_notes:
            note = pretty_midi.Note(
                velocity=n.velocity,
                pitch=n.pitch,
                start=n.start,
                end=n.end,
            )
            lh.notes.append(note)
        pm.instruments.append(lh)
    
    pm.write(path)


def duration_seconds_to_ticks(start: float, end: float, ticks_per_beat: int, tempo: float) -> tuple[int, int]:
    """Convert start/end seconds to MIDI tick positions."""
    sec_per_tick = 60.0 / (tempo * ticks_per_beat)
    return int(start / sec_per_tick), int(end / sec_per_tick)
