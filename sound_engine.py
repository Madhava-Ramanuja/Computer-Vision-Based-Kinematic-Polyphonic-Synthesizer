"""
AirPiano — Sound Engine
Audio loading, polyphonic playback, sustain logic, volume, and instrument switching.
"""

import os
import pygame
import pygame.mixer

from config import (
    SOUNDS_DIR, SOUND_SAMPLE_RATE, SOUND_BUFFER_SIZE,
    PYGAME_CHANNELS, DEFAULT_VOLUME, VOLUME_STEP, INSTRUMENTS
)


class SoundEngine:
    """Handles audio playback with polyphonic support using pygame.mixer."""

    def __init__(self):
        self._initialized = False
        self._sounds = {}          # note_name → pygame.Sound
        self._note_channels = {}   # note_name → pygame.Channel (for sustain)
        self._sustain = False
        self._volume = DEFAULT_VOLUME
        self._current_instrument = "Piano"
        self._active_notes = set()  # Currently sounding notes
        self._error_message = None

        self._init_mixer()

    def _init_mixer(self):
        """Initialize pygame mixer."""
        try:
            pygame.mixer.pre_init(
                frequency=SOUND_SAMPLE_RATE,
                size=-16,
                channels=2,
                buffer=SOUND_BUFFER_SIZE
            )
            pygame.mixer.init()
            pygame.mixer.set_num_channels(PYGAME_CHANNELS)
            self._initialized = True
            self._error_message = None
        except Exception as e:
            self._initialized = False
            self._error_message = f"Audio init failed: {e}"
            print(f"[SoundEngine] ERROR: {self._error_message}")

    def load_sounds(self, instrument=None):
        """Load all WAV files for the specified instrument."""
        if not self._initialized:
            return False

        if instrument is None:
            instrument = self._current_instrument

        instrument_dir = SOUNDS_DIR / instrument.lower()

        if not instrument_dir.exists():
            self._error_message = f"Sound directory not found: {instrument_dir}"
            print(f"[SoundEngine] ERROR: {self._error_message}")
            return False

        self._sounds.clear()
        self._note_channels.clear()
        self._active_notes.clear()

        wav_files = list(instrument_dir.glob("*.wav"))
        if not wav_files:
            self._error_message = f"No WAV files in {instrument_dir}"
            return False

        for wav_path in wav_files:
            note_name = wav_path.stem  # e.g., "C4", "Cs4"
            try:
                self._sounds[note_name] = pygame.mixer.Sound(str(wav_path))
            except Exception as e:
                print(f"[SoundEngine] Warning: Could not load {wav_path.name}: {e}")

        self._current_instrument = instrument
        self._error_message = None
        print(f"[SoundEngine] Loaded {len(self._sounds)} sounds for {instrument}")
        return True

    def play_note(self, note, velocity=100):
        """
        Play a note with given velocity (0-127).
        Returns True if successfully played.
        """
        if not self._initialized:
            return False

        sound = self._sounds.get(note)
        if sound is None:
            return False

        # Find a free channel
        channel = pygame.mixer.find_channel()
        if channel is None:
            # Force-stop oldest channel
            channel = pygame.mixer.Channel(0)

        # Set volume based on velocity and master volume
        vol = (velocity / 127.0) * self._volume
        channel.set_volume(vol)
        channel.play(sound)

        # Track for sustain
        self._note_channels[note] = channel
        self._active_notes.add(note)

        return True

    def stop_note(self, note):
        """Stop a specific note's channel (for sustain release)."""
        channel = self._note_channels.get(note)
        if channel and channel.get_busy():
            channel.fadeout(200)  # 200ms fadeout
        self._active_notes.discard(note)
        self._note_channels.pop(note, None)

    def stop_all(self):
        """Stop all currently playing notes."""
        pygame.mixer.stop()
        self._active_notes.clear()
        self._note_channels.clear()

    def set_sustain(self, active):
        """Toggle sustain mode."""
        self._sustain = active
        if not active:
            # Release all sustained notes
            for note in list(self._note_channels.keys()):
                ch = self._note_channels[note]
                if ch and not ch.get_busy():
                    self._active_notes.discard(note)

    @property
    def sustain(self):
        return self._sustain

    def set_volume(self, vol):
        """Set master volume (0.0 – 1.0)."""
        self._volume = max(0.0, min(1.0, vol))

    def volume_up(self):
        self.set_volume(self._volume + VOLUME_STEP)

    def volume_down(self):
        self.set_volume(self._volume - VOLUME_STEP)

    @property
    def volume(self):
        return self._volume

    def set_instrument(self, name):
        """Switch instrument by reloading sounds."""
        if name in INSTRUMENTS:
            self.stop_all()
            self.load_sounds(name)

    @property
    def instrument(self):
        return self._current_instrument

    @property
    def active_note_count(self):
        """Return number of currently playing notes."""
        # Clean up finished notes
        finished = []
        for note, ch in self._note_channels.items():
            if ch and not ch.get_busy():
                finished.append(note)
        for note in finished:
            self._active_notes.discard(note)
            self._note_channels.pop(note, None)
        return len(self._active_notes)

    @property
    def active_notes(self):
        """Return set of currently active note names."""
        # Clean stale entries
        _ = self.active_note_count
        return set(self._active_notes)

    @property
    def is_initialized(self):
        return self._initialized

    @property
    def error_message(self):
        return self._error_message

    def cleanup(self):
        """Cleanup pygame mixer."""
        if self._initialized:
            pygame.mixer.quit()
