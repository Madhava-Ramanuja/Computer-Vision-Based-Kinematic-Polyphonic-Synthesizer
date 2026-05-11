"""
AirPiano — Piano Engine
Key zone layout, press detection, debouncing logic, and octave management.
"""

import time

from config import (
    PIANO_HEIGHT_RATIO, NUM_WHITE_KEYS, DEFAULT_OCTAVE,
    MIN_OCTAVE, MAX_OCTAVE, PRESS_VELOCITY_THRESHOLD, DEBOUNCE_MS,
    NOTE_NAMES, WHITE_NOTES_IN_OCTAVE, BLACK_NOTES_IN_OCTAVE,
    BLACK_KEY_WHITE_OFFSETS, WHITE_NOTE_INDICES, BLACK_NOTE_INDICES,
    DISPLAY_NAMES
)


class PianoEngine:
    """Manages virtual piano key layout, press detection, and state."""

    def __init__(self):
        self.octave = DEFAULT_OCTAVE
        self.keys = []           # list of key dicts
        self.white_keys = []     # references to white key dicts
        self.black_keys = []     # references to black key dicts
        self._debounce = {}      # note_name → last press timestamp
        self._frame_width = 0
        self._frame_height = 0

    def compute_key_zones(self, frame_width, frame_height):
        """
        Calculate pixel bounding boxes for all keys based on current octave.
        Must be called whenever frame size or octave changes.
        """
        self._frame_width = frame_width
        self._frame_height = frame_height
        self.keys = []
        self.white_keys = []
        self.black_keys = []

        piano_top = int(frame_height * (1.0 - PIANO_HEIGHT_RATIO))
        piano_height = frame_height - piano_top

        # White keys: evenly spaced across full width
        white_key_width = frame_width / NUM_WHITE_KEYS

        # Generate white keys
        white_key_data = []
        for i in range(NUM_WHITE_KEYS):
            octave_offset = i // 7
            note_in_octave = i % 7
            note_name = WHITE_NOTES_IN_OCTAVE[note_in_octave]
            octave = self.octave + octave_offset
            full_name = f"{note_name}{octave}"

            # Get display name
            note_idx = NOTE_NAMES.index(note_name)
            display = DISPLAY_NAMES[note_idx]

            x = int(i * white_key_width)
            w = int((i + 1) * white_key_width) - x

            key = {
                "note": full_name,
                "display_name": f"{display}{octave}",
                "type": "white",
                "rect": (x, piano_top, w, piano_height),
                "is_pressed": False,
                "press_time": 0.0,
                "velocity": 0,
                "hover": False,
                "white_index": i,
            }

            self.keys.append(key)
            self.white_keys.append(key)
            white_key_data.append((i, key))

        # Generate black keys — narrower and shorter for realistic look
        black_key_width = int(white_key_width * 0.52)
        black_key_height = int(piano_height * 0.55)

        for octave_offset in range(2):  # 2 octaves
            for bk_idx, white_offset in enumerate(BLACK_KEY_WHITE_OFFSETS):
                global_white_idx = octave_offset * 7 + white_offset
                if global_white_idx + 1 >= NUM_WHITE_KEYS:
                    continue

                note_name = BLACK_NOTES_IN_OCTAVE[bk_idx]
                octave = self.octave + octave_offset
                full_name = f"{note_name}{octave}"

                note_idx = NOTE_NAMES.index(note_name)
                display = DISPLAY_NAMES[note_idx]

                # Position: centered between the two white keys
                left_white_x = int(global_white_idx * white_key_width)
                right_white_x = int((global_white_idx + 1) * white_key_width)
                center_x = (left_white_x + right_white_x) // 2
                x = center_x - black_key_width // 2

                key = {
                    "note": full_name,
                    "display_name": f"{display}{octave}",
                    "type": "black",
                    "rect": (x, piano_top, black_key_width, black_key_height),
                    "is_pressed": False,
                    "press_time": 0.0,
                    "velocity": 0,
                    "hover": False,
                }

                self.keys.append(key)
                self.black_keys.append(key)

    def check_press(self, fingertips_with_velocity, frame_height):
        """
        Check if any fingertips are pressing keys.

        Args:
            fingertips_with_velocity: list of (px, py, vy, finger_name, hand_index) tuples
            frame_height: frame height in pixels

        Returns:
            list of (note_name, velocity) tuples for newly pressed notes
        """
        pressed = []
        current_time = time.time() * 1000  # ms

        # Reset hover states
        for key in self.keys:
            key["hover"] = False

        for px, py, vy, finger_name, hand_idx in fingertips_with_velocity:
            # Check black keys first (they're on top)
            hit_key = None
            for key in self.black_keys:
                if self._point_in_rect(px, py, key["rect"]):
                    hit_key = key
                    break

            # If not on a black key, check white keys
            if hit_key is None:
                for key in self.white_keys:
                    if self._point_in_rect(px, py, key["rect"]):
                        hit_key = key
                        break

            if hit_key is None:
                continue

            # Mark hover
            hit_key["hover"] = True

            # Check if downward velocity exceeds threshold
            if vy < PRESS_VELOCITY_THRESHOLD:
                continue

            # Hysteresis (Check debounce)
            note = hit_key["note"]
            last_press = self._debounce.get(note, 0)
            if current_time - last_press < DEBOUNCE_MS:
                continue

            # Trigger press!
            # Ensure velocity is audible (min 60) and scales up with faster taps
            velocity = max(60, min(127, int(vy * 5) + 60))
            hit_key["is_pressed"] = True
            hit_key["press_time"] = time.time()
            hit_key["velocity"] = velocity
            self._debounce[note] = current_time

            pressed.append((note, velocity))

        return pressed

    def update(self, dt):
        """Update key animation states. dt is in seconds."""
        current_time = time.time()
        for key in self.keys:
            if key["is_pressed"]:
                elapsed = current_time - key["press_time"]
                if elapsed > 0.5:  # Clear press state after 500ms
                    key["is_pressed"] = False
                    key["velocity"] = 0

    def shift_octave(self, delta):
        """Shift the octave range by delta (±1)."""
        new_octave = self.octave + delta
        if MIN_OCTAVE <= new_octave <= MAX_OCTAVE:
            self.octave = new_octave
            self.compute_key_zones(self._frame_width, self._frame_height)
            return True
        return False

    def get_piano_top(self):
        """Return the Y coordinate of the piano area top."""
        return int(self._frame_height * (1.0 - PIANO_HEIGHT_RATIO))

    def _point_in_rect(self, px, py, rect):
        """Check if point (px, py) is inside rectangle (x, y, w, h)."""
        x, y, w, h = rect
        return x <= px <= x + w and y <= py <= y + h
