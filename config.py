"""
Configuration & Constants
All magic numbers, color palettes, layout settings, and tuning parameters.
"""

import os
from pathlib import Path

# ──────────────────────────────────────────────
# PATHS
# ──────────────────────────────────────────────
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = BASE_DIR / "assets"
SOUNDS_DIR = ASSETS_DIR / "sounds"

# ──────────────────────────────────────────────
# FRAME / DISPLAY
# ──────────────────────────────────────────────
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
FPS_TARGET = 30

# ──────────────────────────────────────────────
# PIANO LAYOUT
# ──────────────────────────────────────────────
PIANO_HEIGHT_RATIO = 0.48       # Piano takes bottom 48% of frame
NUM_WHITE_KEYS = 14             # 2 octaves of white keys
DEFAULT_OCTAVE = 3              # Starting octave (C3–B4)
MIN_OCTAVE = 3                  # We only generated sounds for octaves 3, 4, 5
MAX_OCTAVE = 4                  # At octave 4, it shows 4 and 5.

# ──────────────────────────────────────────────
# PRESS DETECTION
# ──────────────────────────────────────────────
PRESS_VELOCITY_THRESHOLD = 0   # ANY downward motion (even 0) triggers if inside key
DEBOUNCE_MS = 150               # Minimum ms between re-triggers per key

# ──────────────────────────────────────────────
# MEDIAPIPE
# ──────────────────────────────────────────────
MEDIAPIPE_MAX_HANDS = 2
MEDIAPIPE_DETECTION_CONF = 0.72
MEDIAPIPE_TRACKING_CONF = 0.65
PINCH_DISTANCE_PX = 40         # Max distance for pinch gesture

# ──────────────────────────────────────────────
# AUDIO / PYGAME
# ──────────────────────────────────────────────
SOUND_SAMPLE_RATE = 44100
SOUND_BUFFER_SIZE = 1024
PYGAME_CHANNELS = 32
DEFAULT_VOLUME = 0.7
VOLUME_STEP = 0.05

# ──────────────────────────────────────────────
# ADSR ENVELOPE
# ──────────────────────────────────────────────
ADSR_ATTACK_MS = 10
ADSR_DECAY_MS = 200
ADSR_SUSTAIN_LEVEL = 0.6
ADSR_RELEASE_MS = 500

# ──────────────────────────────────────────────
# VISUAL EFFECTS
# ──────────────────────────────────────────────
PARTICLE_COUNT = 12             # Particles per note trigger
RIPPLE_DURATION_MS = 400        # Ripple ring expansion duration
KEY_PRESS_ANIM_MS = 300         # Press flash animation duration
HUD_HEIGHT = 70                 # Top HUD bar height in px
SIDE_PANEL_WIDTH = 180          # Left side panel width in px
STARTUP_ANIM_DURATION_S = 2.0  # Startup animation length
HISTORY_FADE_S = 3.0            # Note history ticker fade time
HISTORY_MAX = 6                 # Max notes shown in history

# ──────────────────────────────────────────────
# COLOR PALETTE  (BGR for OpenCV)
# ──────────────────────────────────────────────
COLORS = {
    "bg_overlay":          (15, 5, 5),            # Near-black blue-black (BGR)
    "accent_cyan":         (255, 240, 0),          # Electric cyan (BGR)
    "accent_gold":         (50, 200, 255),         # Premium gold (BGR)
    "accent_purple":       (255, 60, 160),         # Deep violet (BGR)
    "white_key_base":      (235, 225, 220),        # Cool white
    "white_key_pressed":   (255, 240, 0),          # Cyan flash
    "black_key_base":      (25, 15, 15),           # Near black
    "black_key_pressed":   (255, 60, 160),         # Purple flash
    "glow_soft":           (200, 180, 0),          # Soft teal glow
    "particle_colors": [
        (255, 240, 0),     # Cyan
        (50, 200, 255),    # Gold
        (255, 60, 160),    # Purple
        (120, 80, 255),    # Pink
    ],
    "hud_text":            (230, 210, 200),        # Soft blue-white
    "danger_red":          (60, 60, 255),          # Red
    "skeleton_line":       (120, 100, 0),          # Dim cyan
    "skeleton_joint":      (180, 150, 0),          # Brighter cyan
    "header_bg":           (20, 15, 10),           # Dark header
    "panel_bg":            (25, 20, 15),           # Dark panel
    "recording_red":       (50, 50, 240),          # Pulsing red
    "sustain_green":       (80, 220, 60),          # Green indicator
    "guide_text":          (200, 200, 180),        # Guide overlay text
}

# ──────────────────────────────────────────────
# FINGER COLORS  (BGR)
# ──────────────────────────────────────────────
FINGER_COLORS = {
    "THUMB":  (255, 255, 255),   # White
    "INDEX":  (255, 240, 0),     # Cyan
    "MIDDLE": (50, 200, 255),    # Gold
    "RING":   (255, 60, 160),    # Purple
    "PINKY":  (120, 80, 255),    # Pink
}

# ──────────────────────────────────────────────
# MUSICAL CONSTANTS
# ──────────────────────────────────────────────
NOTE_NAMES = ["C", "Cs", "D", "Ds", "E", "F", "Fs", "G", "Gs", "A", "As", "B"]
DISPLAY_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

WHITE_NOTE_INDICES = [0, 2, 4, 5, 7, 9, 11]   # C D E F G A B
BLACK_NOTE_INDICES = [1, 3, 6, 8, 10]          # C# D# F# G# A#

# White key names within one octave: C, D, E, F, G, A, B
WHITE_NOTES_IN_OCTAVE = ["C", "D", "E", "F", "G", "A", "B"]
BLACK_NOTES_IN_OCTAVE = ["Cs", "Ds", "Fs", "Gs", "As"]

# Black key positions relative to white keys (which white key pairs they sit between)
# In a standard piano: C#(0-1), D#(1-2), F#(3-4), G#(4-5), A#(5-6)
BLACK_KEY_WHITE_OFFSETS = [0, 1, 3, 4, 5]  # index of left white key for each black key

# Instrument definitions
INSTRUMENTS = ["Piano", "Marimba", "Organ"]

# ──────────────────────────────────────────────
# FREQUENCY TABLE (A4 = 440 Hz)
# ──────────────────────────────────────────────
def note_to_freq(note_name, octave):
    """Convert note name + octave to frequency in Hz."""
    semitone_map = {
        "C": -9, "Cs": -8, "D": -7, "Ds": -6, "E": -5,
        "F": -4, "Fs": -3, "G": -2, "Gs": -1, "A": 0,
        "As": 1, "B": 2
    }
    semitones_from_a4 = semitone_map[note_name] + (octave - 4) * 12
    return 440.0 * (2.0 ** (semitones_from_a4 / 12.0))
