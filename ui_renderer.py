"""
AirPiano — Premium UI Renderer (Optimized)
All drawing: piano keys, HUD, animations, particles, glow effects, hand skeleton.
Everything rendered directly onto the OpenCV video frame.

PERFORMANCE: Avoids GaussianBlur, minimizes frame.copy(), uses ROI ops.
"""

import math
import time
import random

import cv2
import numpy as np

from config import (
    COLORS, FINGER_COLORS, PIANO_HEIGHT_RATIO, HUD_HEIGHT, SIDE_PANEL_WIDTH,
    PARTICLE_COUNT, RIPPLE_DURATION_MS, KEY_PRESS_ANIM_MS,
    STARTUP_ANIM_DURATION_S, HISTORY_FADE_S, HISTORY_MAX, INSTRUMENTS
)




class UIRenderer:
    """Premium visual rendering engine for AirPiano — optimized for performance."""

    def __init__(self):
        self._note_history = []
        self._start_time = time.time()
        self._startup_done = False
        self._wave_phase = 0.0
        # Pre-cached gradient line (computed once)
        self._gradient_line = None
        self._cached_width = 0

    def _ensure_gradient_line(self, w):
        """Pre-compute the HUD gradient line (only when width changes)."""
        if w != self._cached_width:
            self._gradient_line = np.zeros((2, w, 3), dtype=np.uint8)
            for i in range(w):
                p = i / w
                b = int(255 * (1 - p) + 255 * p)
                g = int(240 * (1 - p) + 60 * p)
                r = int(0 * (1 - p) + 160 * p)
                self._gradient_line[:, i] = (b, g, r)
            self._cached_width = w

    def render(self, frame, hands, keys, pressed_notes, fps, state):
        """Main render pipeline — called every frame."""
        h, w = frame.shape[:2]
        now = time.time()

        # Startup animation check
        elapsed_since_start = now - self._start_time
        if not self._startup_done and elapsed_since_start < STARTUP_ANIM_DURATION_S:
            return self._render_startup(frame, elapsed_since_start)
        self._startup_done = True

        # Add pressed notes to history
        for note, vel in pressed_notes:
            self._note_history.append((note, now))

        # Clean old history
        if len(self._note_history) > HISTORY_MAX + 5:
            self._note_history = [
                (n, t) for n, t in self._note_history
                if now - t < HISTORY_FADE_S
            ]

        # ── RENDERING PIPELINE ──
        self._draw_piano_background(frame)
        self._draw_white_keys(frame, keys)
        self._draw_black_keys(frame, keys)
        self._draw_fingertips(frame, hands, keys, now)
        self._draw_skeleton(frame, hands)
        self._draw_waveform(frame, state)
        self._draw_history(frame, now)

        if state.get('hands_count', 0) == 0:
            self._draw_no_hands_guide(frame, now)

        error = state.get('error_message')
        if error:
            self._draw_error(frame, error)

        return frame

    # ═══════════════════════════════════════════════
    # A) BACKGROUND — ROI blend only (no full copy)
    # ═══════════════════════════════════════════════

    def _draw_piano_background(self, frame):
        h, w = frame.shape[:2]
        piano_top = int(h * (1.0 - PIANO_HEIGHT_RATIO))
        roi = frame[piano_top:h, 0:w]
        dark = np.full_like(roi, COLORS["bg_overlay"], dtype=np.uint8)
        cv2.addWeighted(dark, 0.7, roi, 0.3, 0, dst=roi)

    # ═══════════════════════════════════════════════
    # B) WHITE KEYS — direct draw, no copy/blur
    # ═══════════════════════════════════════════════

    def _draw_white_keys(self, frame, keys):
        now = time.time()
        for key in keys:
            if key["type"] != "white":
                continue

            x, y, kw, kh = key["rect"]
            x2, y2 = x + kw, y + kh

            if key["is_pressed"]:
                elapsed = now - key["press_time"]
                progress = min(1.0, elapsed / (KEY_PRESS_ANIM_MS / 1000.0))
                brightness = 1.0 + math.sin(progress * math.pi) * 0.5
                color = COLORS["white_key_pressed"]
                bright_color = (
                    min(255, int(color[0] * brightness)),
                    min(255, int(color[1] * brightness)),
                    min(255, int(color[2] * brightness)),
                )
                cv2.rectangle(frame, (x + 1, y + 1), (x2 - 1, y2 - 1), bright_color, -1)
                # Simple bright border instead of GaussianBlur glow
                cv2.rectangle(frame, (x - 2, y - 2), (x2 + 2, y2 + 2), COLORS["accent_cyan"], 2)
                cv2.line(frame, (x + 2, y + 2), (x2 - 2, y + 2), (255, 255, 255), 2)

            elif key.get("hover"):
                cv2.rectangle(frame, (x + 1, y + 1), (x2 - 1, y2 - 1), COLORS["white_key_base"], -1)
                cv2.rectangle(frame, (x, y), (x2, y2), COLORS["glow_soft"], 2)
            else:
                cv2.rectangle(frame, (x + 1, y + 1), (x2 - 1, y2 - 1), COLORS["white_key_base"], -1)

            # Border
            cv2.rectangle(frame, (x, y), (x2, y2), (80, 80, 90), 1)

            # Note label
            label = key["display_name"]
            ts = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, 0.4, 1)[0]
            tx = x + (kw - ts[0]) // 2
            ty = y + kh - 10
            cv2.putText(frame, label, (tx, ty), cv2.FONT_HERSHEY_DUPLEX,
                        0.4, (60, 60, 70), 1, cv2.LINE_AA)

    # ═══════════════════════════════════════════════
    # C) BLACK KEYS
    # ═══════════════════════════════════════════════

    def _draw_black_keys(self, frame, keys):
        now = time.time()
        for key in keys:
            if key["type"] != "black":
                continue

            x, y, kw, kh = key["rect"]
            x2, y2 = x + kw, y + kh

            if key["is_pressed"]:
                elapsed = now - key["press_time"]
                progress = min(1.0, elapsed / (KEY_PRESS_ANIM_MS / 1000.0))
                brightness = 1.0 + math.sin(progress * math.pi) * 0.4
                color = COLORS["black_key_pressed"]
                bright_color = (
                    min(255, int(color[0] * brightness)),
                    min(255, int(color[1] * brightness)),
                    min(255, int(color[2] * brightness)),
                )
                cv2.rectangle(frame, (x, y), (x2, y2), bright_color, -1)
                cv2.rectangle(frame, (x - 2, y - 2), (x2 + 2, y2 + 2), COLORS["accent_purple"], 2)
            else:
                cv2.rectangle(frame, (x, y), (x2, y2), COLORS["black_key_base"], -1)
                cv2.rectangle(frame, (x, y), (x2, y2), (60, 30, 50), 1)

    # ═══════════════════════════════════════════════
    # D) FINGERTIP VISUALIZATION
    # ═══════════════════════════════════════════════

    def _draw_fingertips(self, frame, hands, keys, now):
        pulse = math.sin(now * 3) * 3

        for hand in hands:
            for finger_name, (px, py) in hand["fingertips"].items():
                color = FINGER_COLORS.get(finger_name, (255, 255, 255))
                outer_r = int(15 + pulse)
                cv2.circle(frame, (px, py), outer_r, color, 2, cv2.LINE_AA)
                cv2.circle(frame, (px, py), 7, color, -1, cv2.LINE_AA)

                # Hover indicator triangle
                for key in keys:
                    kx, ky, kw, kh = key["rect"]
                    if kx <= px <= kx + kw and ky <= py <= ky + kh:
                        tri_cx = kx + kw // 2
                        tri_y = ky - 15
                        pts = np.array([
                            [tri_cx - 6, tri_y - 8],
                            [tri_cx + 6, tri_y - 8],
                            [tri_cx, tri_y + 2],
                        ], dtype=np.int32)
                        cv2.fillPoly(frame, [pts], color)
                        break

    # ═══════════════════════════════════════════════
    # E) HAND SKELETON 
    # ═══════════════════════════════════════════════

    def _draw_skeleton(self, frame, hands):
        for hand in hands:
            pixel_lm = hand["pixel_landmarks"]
            connections = hand.get("connections", [])
            for s, e in connections:
                cv2.line(frame, pixel_lm[s], pixel_lm[e], COLORS["skeleton_line"], 1, cv2.LINE_AA)
            for px, py in pixel_lm:
                cv2.circle(frame, (px, py), 3, COLORS["skeleton_joint"], -1, cv2.LINE_AA)


    # ═══════════════════════════════════════════════
    # F) SOUND WAVE VISUALIZATION
    # ═══════════════════════════════════════════════

    def _draw_waveform(self, frame, state):
        h, w = frame.shape[:2]
        piano_top = int(h * (1.0 - PIANO_HEIGHT_RATIO))
        wave_y = piano_top - 30

        active_count = len(state.get('active_notes', set()))
        if active_count == 0:
            self._wave_phase += 0.02
            amplitude = 5
        else:
            self._wave_phase += 0.15
            amplitude = min(25, 8 + active_count * 4)

        num_points = 60  # reduced from 80
        start_x = SIDE_PANEL_WIDTH + 20
        end_x = w - 20
        step = (end_x - start_x) / num_points

        points = np.empty((num_points, 1, 2), dtype=np.int32)
        for i in range(num_points):
            px = int(start_x + i * step)
            py = int(wave_y + amplitude * math.sin(
                self._wave_phase + i * 0.3
            ) * math.sin(i * 0.05 + self._wave_phase * 0.5))
            points[i, 0] = (px, py)

        cv2.polylines(frame, [points], False, COLORS["accent_gold"], 2, cv2.LINE_AA)

    # ═══════════════════════════════════════════════
    # J) NOTE HISTORY TICKER
    # ═══════════════════════════════════════════════

    def _draw_history(self, frame, now):
        h, w = frame.shape[:2]
        recent = self._note_history[-HISTORY_MAX:]
        x_pos = w - 120
        y_pos = h - 30

        for note, timestamp in reversed(recent):
            age = now - timestamp
            alpha = max(0.0, 1.0 - age / HISTORY_FADE_S)
            color = (int(COLORS["accent_cyan"][0] * alpha),
                     int(COLORS["accent_cyan"][1] * alpha),
                     int(COLORS["accent_cyan"][2] * alpha))
            cv2.putText(frame, f"{note}  {age:.1f}s", (x_pos, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)
            y_pos -= 22

    # ═══════════════════════════════════════════════
    # K) STARTUP ANIMATION — simplified, no blur
    # ═══════════════════════════════════════════════

    def _render_startup(self, frame, elapsed):
        h, w = frame.shape[:2]
        progress = elapsed / STARTUP_ANIM_DURATION_S

        # Darken frame
        frame[:] = (frame * 0.4).astype(np.uint8)

        # Piano keys rise
        piano_top = int(h * (1.0 - PIANO_HEIGHT_RATIO))
        piano_height = h - piano_top
        num_keys = 14
        key_w = w // num_keys

        for i in range(num_keys):
            key_progress = max(0.0, min(1.0, progress * 2.0 - i * 0.1))
            offset = int((1.0 - key_progress) * piano_height)
            x = i * key_w
            y = piano_top + offset

            flash_time = i * 0.08
            if elapsed > flash_time and elapsed < flash_time + 0.15:
                color = COLORS["accent_cyan"]
            else:
                color = COLORS["white_key_base"]

            if y < h:
                cv2.rectangle(frame, (x + 1, y), (x + key_w - 1, h), color, -1)
                cv2.rectangle(frame, (x, y), (x + key_w, h), (60, 60, 70), 1)

        # Logo
        visible = min(8, int(progress * 16))
        if visible > 0:
            logo = "AIRPIANO"[:visible]
            alpha_f = min(1.0, progress * 2)
            color = (int(COLORS["accent_gold"][0] * alpha_f),
                     int(COLORS["accent_gold"][1] * alpha_f),
                     int(COLORS["accent_gold"][2] * alpha_f))
            ts = cv2.getTextSize(logo, cv2.FONT_HERSHEY_DUPLEX, 2.0, 3)[0]
            cv2.putText(frame, logo, ((w - ts[0]) // 2, h // 3),
                        cv2.FONT_HERSHEY_DUPLEX, 2.0, color, 3, cv2.LINE_AA)

        if progress > 0.5:
            a = min(1.0, (progress - 0.5) * 4)
            sc = (int(COLORS["hud_text"][0] * a),
                  int(COLORS["hud_text"][1] * a),
                  int(COLORS["hud_text"][2] * a))
            sub = "Gesture-Controlled Piano"
            ts = cv2.getTextSize(sub, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 1)[0]
            cv2.putText(frame, sub, ((w - ts[0]) // 2, h // 3 + 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, sc, 1, cv2.LINE_AA)

        return frame

    # ═══════════════════════════════════════════════
    # GUIDE / ERROR OVERLAYS
    # ═══════════════════════════════════════════════

    def _draw_no_hands_guide(self, frame, now):
        h, w = frame.shape[:2]
        pulse = 0.5 + 0.3 * math.sin(now * 2)
        cx, cy = w // 2, h // 2 - 40
        bw, bh = 190, 40

        roi = frame[cy - bh:cy + bh, cx - bw:cx + bw]
        dark = np.full_like(roi, COLORS["header_bg"], dtype=np.uint8)
        cv2.addWeighted(dark, 0.75, roi, 0.25, 0, dst=roi)

        border_color = (int(COLORS["accent_cyan"][0] * pulse),
                        int(COLORS["accent_cyan"][1] * pulse),
                        int(COLORS["accent_cyan"][2] * pulse))
        cv2.rectangle(frame, (cx - bw, cy - bh), (cx + bw, cy + bh), border_color, 2)

        msg = "Show your hands to play"
        ts = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)[0]
        color = (int(COLORS["guide_text"][0] * pulse),
                 int(COLORS["guide_text"][1] * pulse),
                 int(COLORS["guide_text"][2] * pulse))
        cv2.putText(frame, msg, (cx - ts[0] // 2, cy + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1, cv2.LINE_AA)

    def _draw_error(self, frame, error_msg):
        h, w = frame.shape[:2]
        roi = frame[h - 40:h, 0:w]
        dark = np.full_like(roi, (0, 0, 60), dtype=np.uint8)
        cv2.addWeighted(dark, 0.85, roi, 0.15, 0, dst=roi)
        cv2.putText(frame, f"ERROR: {error_msg}", (10, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS["danger_red"], 1, cv2.LINE_AA)
