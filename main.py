"""
Main Entry Point - AirPiano
---------------------------
This script acts as the Orchestrator. It does not perform heavy math or graphics rendering itself. 
Instead, it enforces a strict Separation of Concerns, managing the data pipeline between the 
Vision, Physics, Audio, and UI modules to maintain a real-time 30 FPS processing loop.
"""

import os
import sys
import time

import cv2
import numpy as np

# Configuration constants for hardware and thresholds
from config import (
    FRAME_WIDTH, FRAME_HEIGHT, FPS_TARGET, SOUNDS_DIR,
    PRESS_VELOCITY_THRESHOLD, INSTRUMENTS
)

# Importing the 5 Core Pillars of the Architecture
from hand_tracker import HandTracker       # MediaPipe Perception Layer
from piano_engine import PianoEngine       # Kinematic Physics & Schmitt Trigger
from sound_engine import SoundEngine       # Pygame 32-Channel DSP
from ui_renderer import UIRenderer         # Stateless Graphics Pipeline
from recorder import Recorder              # Asynchronous JSON/MIDI Serialization
from generate_sounds import generate_all_instruments


def ensure_sounds_exist():
    """
    Pre-flight Check: Ensures the audio buffer has files to load.
    If the system is running for the first time, it triggers Additive Synthesis
    to generate all 37 piano keys mathematically before the camera turns on.
    """
    piano_dir = SOUNDS_DIR / "piano"
    if not piano_dir.exists() or len(list(piano_dir.glob("*.wav"))) < 37:
        print("[AirPiano] First run detected — generating sound samples...")
        generate_all_instruments()
        print("[AirPiano] Sound generation complete!")
    else:
        print("[AirPiano] Sound samples found.")


def main():
    """Main application orchestrator loop."""
    print("=" * 55)
    print("  ✦  A I R P I A N O  ✦")
    print("  Premium Gesture-Controlled Piano")
    print("=" * 55)
    print()

    # ─── Step 1: Pre-Flight Check ───
    ensure_sounds_exist()

    # ─── Step 2: Initialize Core Modules ───
    print("[AirPiano] Initializing modules...")
    tracker = HandTracker()   # The Eyes: Initializes MediaPipe CNN
    piano = PianoEngine()     # The Brain: Initializes Spatial Logic
    sound = SoundEngine()     # The Voice: Initializes SDL/Pygame Audio Buffer
    renderer = UIRenderer()   # The Painter: Initializes OpenCV Drawing routines
    recorder = Recorder()     # The Scribe: Initializes in-memory event logging

    # Load default instrument sounds into RAM to prevent disk-read latency later
    if sound.is_initialized:
        sound.load_sounds("Piano")
    else:
        print("[AirPiano] WARNING: Audio system not available. Continuing without sound.")

    # ─── Step 3: Hardware Interface Setup (Webcam) ───
    print("[AirPiano] Opening camera...")
    cap = cv2.VideoCapture(0) # Grabs the default OS video device
    if not cap.isOpened():
        print("[AirPiano] ERROR: Could not open camera!")
        sys.exit(1)

    # Request specific resolution from the camera hardware
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    # VERIFICATION: The camera might not support our requested resolution.
    # We must pull the *actual* hardware resolution it defaulted to.
    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[AirPiano] Camera resolution: {actual_w}x{actual_h}")

    # Inject the actual resolution into the Physics Engine so the Axis-Aligned 
    # Bounding Boxes (AABB) for the keys scale perfectly to the screen.
    piano.compute_key_zones(actual_w, actual_h)

    # ─── Real-Time State Variables ───
    fps = 0.0
    frame_count = 0
    fps_timer = time.time()

    # Cooldown timers prevent gesture-spamming (e.g., shifting octaves 10 times a second)
    last_pinch_time = 0.0
    pinch_cooldown = 0.8  # seconds
    last_fist_time = 0.0
    fist_cooldown = 0.5

    print("[AirPiano] Ready! Press ESC to quit.")
    print()

    # ─── Step 4: The Core Event Loop (~30 Hz) ───
    try:
        while True:
            # Grab the raw RGB matrix from the webcam
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            # MIRROR INVERSION: Extremely important for UX. 
            # If we don't flip the X-axis (1), moving the physical hand left 
            # will move the virtual hand right, making it unplayable.
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]

            # ─── Step 5: The Perception Layer ───
            # Pass the frame to MediaPipe. It returns an array of structured
            # dictionaries containing 21 (x, y, z) landmarks for each detected hand.
            hands = tracker.process(frame)

            # ─── Step 6: Kinematic Data Extraction ───
            all_fingertips = []
            for hand in hands:
                hand_idx = hand["hand_index"]
                for finger_name, (px, py) in hand["fingertips"].items():
                    
                    # Ignore the thumb for striking keys; save it for control gestures
                    if finger_name == "THUMB":
                        continue
                    
                    # Calculate dy/dt (Instantaneous Vertical Velocity) for this frame
                    dx, dy = tracker.get_fingertip_velocity(hand_idx, finger_name, (px, py))
                    
                    # Append the coordinate AND the velocity for the physics engine
                    all_fingertips.append((px, py, dy, finger_name, hand_idx))

            # ─── Step 7: The Physics Layer (Patent Core) ───
            # Pass the coordinates and velocities into the PianoEngine.
            # This is where the Schmitt Trigger (Spatial Hysteresis) and 
            # Velocity Thresholds filter out hovers and micro-jitter.
            pressed_notes = piano.check_press(all_fingertips, h)

            # ─── Step 8: Audio & Data Persistence Layer ───
            # If the Physics Layer validated a strike, it returns the note and strike speed.
            for note, velocity in pressed_notes:
                # Bypasses the Python GIL by pushing audio to the C-level Pygame buffer
                sound.play_note(note, velocity)
                
                # Asynchronously append the event to memory if recording is active
                if recorder.recording:
                    recorder.log_note(note, velocity)

            # ─── Step 9: Control Gestures Layer ───
            current_time = time.time()
            for hand in hands:
                # PINCH: Shift the keyboard octave left or right
                if tracker.is_pinch(hand) and current_time - last_pinch_time > pinch_cooldown:
                    if hand["handedness"] == "Left":
                        piano.shift_octave(-1)
                    else:
                        piano.shift_octave(1)
                    last_pinch_time = current_time

                # OPEN PALM: Activate the piano sustain pedal
                if tracker.is_open_palm(hand):
                    sound.set_sustain(True)

                # FIST: Release the sustain pedal
                if tracker.is_fist(hand) and current_time - last_fist_time > fist_cooldown:
                    sound.set_sustain(False)
                    last_fist_time = current_time

            # Update mathematical animations (e.g., fading glowing keys)
            piano.update(1.0 / max(fps, 1.0))

            # ─── Step 10: State Packaging ───
            # Bundle all active system variables so the stateless UI renderer 
            # knows exactly what data to paint onto the screen.
            state = {
                'octave': piano.octave,
                'volume': sound.volume,
                'instrument': sound.instrument,
                'sustain': sound.sustain,
                'recording': recorder.recording,
                'rec_elapsed_ms': recorder.elapsed_ms,
                'rec_events': recorder.event_count,
                'playing_back': recorder.is_playing_back,
                'hands_count': len(hands),
                'active_notes': sound.active_notes,
                'error_message': sound.error_message,
            }

            # ─── Step 11: The UI Rendering Layer ───
            # Pass the raw frame, physics bounding boxes (keys), and state variables
            # to the Renderer. Because this is stateless, it causes zero physics lag.
            frame = renderer.render(frame, hands, piano.keys, pressed_notes, fps, state)

            # ─── Step 12: Hardware Input & Application Display ───
            # cv2.waitKey(1) is required to refresh the OpenCV window, but it also
            # captures physical keyboard strokes for manual overrides.
            key = cv2.waitKey(1) & 0xFF

            if key == 27:  # ESC Key triggers graceful shutdown
                print("[AirPiano] Quitting...")
                break
            elif key == ord('r') or key == ord('R'):
                if recorder.recording: recorder.stop_recording()
                else: recorder.start_recording()
            elif key == ord('p') or key == ord('P'):
                if not recorder.recording and not recorder.is_playing_back:
                    recorder.playback(sound)
            elif key == ord('m') or key == ord('M'):
                if not recorder.recording:
                    path = recorder.export_midi()
                    if path: print(f"[AirPiano] MIDI saved: {path}")
            elif key == ord('j') or key == ord('J'):
                if not recorder.recording:
                    path = recorder.export_json()
                    if path: print(f"[AirPiano] JSON saved: {path}")
            elif key == 0: piano.shift_octave(1)   # Up Arrow
            elif key == 1: piano.shift_octave(-1)  # Down Arrow
            elif key == ord('1'): sound.set_instrument("Piano")
            elif key == ord('2'): sound.set_instrument("Marimba")
            elif key == ord('3'): sound.set_instrument("Organ")
            elif key == ord('v') or key == ord('V'): sound.volume_up()
            elif key == ord('b') or key == ord('B'): sound.volume_down()

            # Paint the fully rendered frame to the user's monitor
            cv2.imshow("AirPiano", frame)

            # ─── Mathematical FPS Calculation ───
            # Tracks true performance Delta Time rather than assuming 30 FPS.
            frame_count += 1
            elapsed = time.time() - fps_timer
            if elapsed >= 1.0:
                fps = frame_count / elapsed
                frame_count = 0
                fps_timer = time.time()

    except KeyboardInterrupt:
        print("\n[AirPiano] Interrupted by user.")

    finally:
        # ─── Graceful Shutdown ───
        # This block ensures memory leaks do not occur if the app crashes or stops.
        print("[AirPiano] Cleaning up...")
        cap.release()                # Frees the webcam for other apps
        cv2.destroyAllWindows()      # Destroys UI windows
        tracker.release()            # Cleans up MediaPipe GPU/CPU threads
        sound.cleanup()              # Safely flushes the Pygame C-level audio buffer
        print("[AirPiano] Goodbye!")

if __name__ == "__main__":
    main()