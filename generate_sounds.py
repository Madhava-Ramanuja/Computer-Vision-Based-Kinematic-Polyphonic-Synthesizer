"""
AirPiano — Sound Generator
Generates piano-like WAV samples using additive synthesis + ADSR envelope.
Supports multiple instrument timbres: Piano, Marimba, Organ.
Run standalone or called from main.py on first launch.
"""

import os
import numpy as np
from scipy.io import wavfile
from pathlib import Path

from config import (
    SOUNDS_DIR, SOUND_SAMPLE_RATE, NOTE_NAMES,
    ADSR_ATTACK_MS, ADSR_DECAY_MS, ADSR_SUSTAIN_LEVEL, ADSR_RELEASE_MS,
    note_to_freq, INSTRUMENTS
)


def generate_adsr_envelope(num_samples, sample_rate, attack_ms, decay_ms,
                           sustain_level, release_ms):
    """Generate an ADSR amplitude envelope."""
    attack_samples = int(sample_rate * attack_ms / 1000.0)
    decay_samples = int(sample_rate * decay_ms / 1000.0)
    release_samples = int(sample_rate * release_ms / 1000.0)
    sustain_samples = max(0, num_samples - attack_samples - decay_samples - release_samples)

    envelope = np.zeros(num_samples, dtype=np.float64)

    idx = 0
    # Attack: 0 → 1
    if attack_samples > 0:
        end = min(idx + attack_samples, num_samples)
        envelope[idx:end] = np.linspace(0.0, 1.0, end - idx, endpoint=False)
        idx = end

    # Decay: 1 → sustain_level
    if decay_samples > 0 and idx < num_samples:
        end = min(idx + decay_samples, num_samples)
        envelope[idx:end] = np.linspace(1.0, sustain_level, end - idx, endpoint=False)
        idx = end

    # Sustain: hold at sustain_level
    if sustain_samples > 0 and idx < num_samples:
        end = min(idx + sustain_samples, num_samples)
        envelope[idx:end] = sustain_level
        idx = end

    # Release: sustain_level → 0
    if idx < num_samples:
        end = num_samples
        envelope[idx:end] = np.linspace(sustain_level, 0.0, end - idx, endpoint=True)

    return envelope


def generate_piano_tone(frequency, duration_s, sample_rate, instrument="Piano"):
    """Generate a single note using additive synthesis with instrument-specific timbres."""
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)

    if instrument == "Piano":
        # Rich piano: fundamental + harmonics with natural decay
        harmonic_amplitudes = [1.0, 0.5, 0.25, 0.15, 0.08]
        harmonic_decays = [1.0, 1.5, 2.0, 2.5, 3.0]  # faster decay for higher harmonics
        wave = np.zeros_like(t)
        for i, (amp, decay_rate) in enumerate(zip(harmonic_amplitudes, harmonic_decays)):
            harmonic_freq = frequency * (i + 1)
            if harmonic_freq > sample_rate / 2:
                break  # Nyquist limit
            decay_env = np.exp(-decay_rate * t)
            wave += amp * decay_env * np.sin(2 * np.pi * harmonic_freq * t) #sine wave equation used to develope sound
        # Add slight inharmonicity (like real piano strings)
        inharm = 0.0005
        for i in range(1, 4):
            harmonic_freq = frequency * (i + 1) * (1 + inharm * (i + 1) ** 2)
            if harmonic_freq < sample_rate / 2:
                wave += 0.02 * np.sin(2 * np.pi * harmonic_freq * t) * np.exp(-3.0 * t)

    elif instrument == "Marimba":
        # Marimba: sharp attack, few harmonics, fast decay
        harmonic_amplitudes = [1.0, 0.3, 0.05]
        wave = np.zeros_like(t)
        for i, amp in enumerate(harmonic_amplitudes):
            harmonic_freq = frequency * (i + 1)
            if harmonic_freq > sample_rate / 2:
                break
            wave += amp * np.sin(2 * np.pi * harmonic_freq * t)
        # Add the characteristic "wooden" overtone
        wave += 0.15 * np.sin(2 * np.pi * frequency * 4.0 * t) * np.exp(-8.0 * t)

    elif instrument == "Organ":
        # Organ: sustained, equal-ish harmonics, no natural decay
        harmonic_amplitudes = [1.0, 0.7, 0.5, 0.4, 0.3, 0.2]
        wave = np.zeros_like(t)
        for i, amp in enumerate(harmonic_amplitudes):
            harmonic_freq = frequency * (i + 1)
            if harmonic_freq > sample_rate / 2:
                break
            wave += amp * np.sin(2 * np.pi * harmonic_freq * t)
        # Add slight vibrato for realism
        vibrato_rate = 5.5  # Hz
        vibrato_depth = 0.003
        wave *= (1.0 + vibrato_depth * np.sin(2 * np.pi * vibrato_rate * t))

    else:
        wave = np.sin(2 * np.pi * frequency * t)

    # Normalize
    peak = np.max(np.abs(wave))
    if peak > 0:
        wave = wave / peak

    return wave


def generate_note_wav(note_name, octave, output_dir, sample_rate, instrument="Piano"):
    """Generate and save a single note as a WAV file."""
    frequency = note_to_freq(note_name, octave)
    duration_s = 2.0  # 2 seconds per note

    # Generate tone
    wave = generate_piano_tone(frequency, duration_s, sample_rate, instrument)

    # Apply ADSR envelope
    if instrument == "Marimba":
        envelope = generate_adsr_envelope(
            len(wave), sample_rate,
            attack_ms=5, decay_ms=100, sustain_level=0.2, release_ms=300
        )
    elif instrument == "Organ":
        envelope = generate_adsr_envelope(
            len(wave), sample_rate,
            attack_ms=30, decay_ms=50, sustain_level=0.9, release_ms=200
        )
    else:  # Piano
        envelope = generate_adsr_envelope(
            len(wave), sample_rate,
            ADSR_ATTACK_MS, ADSR_DECAY_MS, ADSR_SUSTAIN_LEVEL, ADSR_RELEASE_MS
        )

    wave *= envelope

    # Convert to 16-bit PCM
    wave_int16 = np.int16(wave * 32767 * 0.8)  # 0.8 to prevent clipping

    # Save
    filename = f"{note_name}{octave}.wav"
    filepath = os.path.join(output_dir, filename)
    wavfile.write(filepath, sample_rate, wave_int16)
    return filepath


def generate_all_sounds(instrument="Piano", force=False):
    """Generate all chromatic notes from C3 to C6 for a given instrument."""
    instrument_dir = SOUNDS_DIR / instrument.lower()
    instrument_dir.mkdir(parents=True, exist_ok=True)

    # Check if sounds already exist
    existing = list(instrument_dir.glob("*.wav"))
    if len(existing) >= 37 and not force:
        print(f"[SoundGen] {instrument} sounds already exist ({len(existing)} files). Skipping.")
        return

    print(f"[SoundGen] Generating {instrument} sounds...")
    count = 0

    # C3 to B5
    for octave in range(3, 6):
        for note_name in NOTE_NAMES:
            filepath = generate_note_wav(
                note_name, octave, str(instrument_dir),
                SOUND_SAMPLE_RATE, instrument
            )
            count += 1
            print(f"  Generated: {os.path.basename(filepath)}")

    # C6 (the final note)
    filepath = generate_note_wav("C", 6, str(instrument_dir), SOUND_SAMPLE_RATE, instrument)
    count += 1
    print(f"  Generated: {os.path.basename(filepath)}")

    print(f"[SoundGen] Done! Generated {count} {instrument} samples.")


def generate_all_instruments(force=False):
    """Generate sounds for all instruments."""
    for instrument in INSTRUMENTS:
        generate_all_sounds(instrument, force)


if __name__ == "__main__":
    print("=" * 50)
    print("  AirPiano Sound Generator")
    print("=" * 50)
    generate_all_instruments(force=True)
    print("\nAll instruments generated successfully!")
