"""
AirPiano — Recorder
Record note events with timestamps, playback, MIDI export, and JSON export.
"""

import json
import os
import time
import threading
from pathlib import Path

import mido

from config import ASSETS_DIR, NOTE_NAMES


class Recorder:
    """Records, plays back, and exports note events."""

    def __init__(self):
        self.recording = False
        self._buffer = []
        self._start_time = 0.0
        self._playback_thread = None
        self._playing_back = False

    def start_recording(self):
        """Start recording note events."""
        self._buffer.clear()
        self._start_time = time.time()
        self.recording = True
        print("[Recorder] Recording started.")

    def stop_recording(self):
        """Stop recording and return the buffer."""
        self.recording = False
        print(f"[Recorder] Recording stopped. {len(self._buffer)} events captured.")
        return list(self._buffer)

    def log_note(self, note, velocity=100):
        """Log a note event with timestamp (ms since start)."""
        if not self.recording:
            return
        elapsed_ms = int((time.time() - self._start_time) * 1000)
        event = {
            "note": note,
            "time": elapsed_ms,
            "velocity": velocity,
        }
        self._buffer.append(event)

    @property
    def buffer(self):
        return list(self._buffer)

    @property
    def event_count(self):
        return len(self._buffer)

    @property
    def elapsed_ms(self):
        if not self.recording:
            return 0
        return int((time.time() - self._start_time) * 1000)

    # ─────────────────────────────────────────
    # PLAYBACK
    # ─────────────────────────────────────────

    def playback(self, sound_engine, buffer=None):
        """Replay recorded notes using a background thread."""
        if self._playing_back:
            return
        buf = buffer if buffer is not None else self._buffer
        if not buf:
            print("[Recorder] Nothing to play back.")
            return

        self._playing_back = True
        self._playback_thread = threading.Thread(
            target=self._playback_worker,
            args=(sound_engine, list(buf)),
            daemon=True
        )
        self._playback_thread.start()

    def _playback_worker(self, sound_engine, buf):
        """Worker thread for playback."""
        try:
            start = time.time()
            for event in buf:
                target_time = event["time"] / 1000.0
                elapsed = time.time() - start
                wait = target_time - elapsed
                if wait > 0:
                    time.sleep(wait)
                sound_engine.play_note(event["note"], event.get("velocity", 100))
        finally:
            self._playing_back = False
            print("[Recorder] Playback finished.")

    @property
    def is_playing_back(self):
        return self._playing_back

    # ─────────────────────────────────────────
    # MIDI EXPORT
    # ─────────────────────────────────────────

    def export_midi(self, buffer=None, filename=None):
        """Export recorded notes as a MIDI file."""
        buf = buffer if buffer is not None else self._buffer
        if not buf:
            print("[Recorder] No events to export.")
            return None

        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"airpiano_recording_{timestamp}.mid"

        exports_dir = ASSETS_DIR / "recordings"
        exports_dir.mkdir(parents=True, exist_ok=True)
        filepath = exports_dir / filename

        mid = mido.MidiFile()
        track = mido.MidiTrack()
        mid.tracks.append(track)

        # Set tempo (120 BPM)
        track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(120)))
        track.append(mido.MetaMessage('track_name', name='AirPiano Recording'))

        # Convert note events to MIDI
        ticks_per_beat = mid.ticks_per_beat  # default 480
        ms_per_beat = 500  # 120 BPM = 500ms per beat

        prev_time_ms = 0
        for event in buf:
            note_name = event["note"]
            midi_note = self._note_to_midi(note_name)
            if midi_note is None:
                continue

            delta_ms = event["time"] - prev_time_ms
            delta_ticks = int(delta_ms * ticks_per_beat / ms_per_beat)
            velocity = min(127, max(1, event.get("velocity", 100)))

            track.append(mido.Message(
                'note_on', note=midi_note, velocity=velocity, time=delta_ticks
            ))
            # Add note_off after 200ms
            note_off_ticks = int(200 * ticks_per_beat / ms_per_beat)
            track.append(mido.Message(
                'note_off', note=midi_note, velocity=0, time=note_off_ticks
            ))

            prev_time_ms = event["time"]

        mid.save(str(filepath))
        print(f"[Recorder] MIDI exported to: {filepath}")
        return str(filepath)

    def _note_to_midi(self, note_str):
        """Convert note string (e.g., 'C4', 'Cs4') to MIDI number."""
        # Parse note name and octave
        if len(note_str) < 2:
            return None

        if note_str[-1].isdigit():
            if len(note_str) >= 3 and note_str[-2].isdigit():
                return None  # invalid
            octave = int(note_str[-1])
            name = note_str[:-1]
        else:
            return None

        if name not in NOTE_NAMES:
            return None

        semitone = NOTE_NAMES.index(name)
        # MIDI: C4 = 60
        midi_note = (octave + 1) * 12 + semitone
        return midi_note

    # ─────────────────────────────────────────
    # JSON EXPORT
    # ─────────────────────────────────────────

    def export_json(self, buffer=None, filename=None):
        """Export recorded notes as a JSON file."""
        buf = buffer if buffer is not None else self._buffer
        if not buf:
            print("[Recorder] No events to export.")
            return None

        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"airpiano_recording_{timestamp}.json"

        exports_dir = ASSETS_DIR / "recordings"
        exports_dir.mkdir(parents=True, exist_ok=True)
        filepath = exports_dir / filename

        with open(filepath, "w") as f:
            json.dump({
                "version": "1.0",
                "events": buf,
                "total_events": len(buf),
                "duration_ms": buf[-1]["time"] if buf else 0,
            }, f, indent=2)

        print(f"[Recorder] JSON exported to: {filepath}")
        return str(filepath)
