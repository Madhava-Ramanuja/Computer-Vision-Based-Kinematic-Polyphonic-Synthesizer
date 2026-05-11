# ✦ AirPiano — Premium AI-Powered Gesture Piano

> Play piano in the air using just your hands and a webcam. No physical keyboard needed.

AirPiano is a real-time gesture-controlled virtual piano that uses **computer vision** and **hand tracking** to let you play music by moving your fingers in front of your webcam. Every note is triggered by natural hand gestures, with beautiful visual feedback, particle effects, and a premium heads-up display.

---

## ✨ Features

- **Real-time hand tracking** — MediaPipe Hands detects both hands with 21 landmarks each
- **Velocity-sensitive key presses** — Harder/faster finger motion = louder notes
- **Full 2-octave piano** — 14 white keys + 10 black keys, octave-shiftable
- **Polyphonic audio** — Play chords with multiple fingers simultaneously (32 channels)
- **3 Instruments** — Piano, Marimba, Organ (synthetically generated tones)
- **Premium visual effects** — Particle bursts, ripple rings, glow effects, pulsing indicators
- **Heads-up display** — FPS, active notes, volume, recording status, hand count
- **Recording & export** — Record sessions, playback, export as MIDI or JSON
- **Gesture controls** — Pinch to shift octave, open palm for sustain, fist to release
- **Startup animation** — Cinematic key sweep and logo reveal on launch

---

## 🛠 Installation

### Requirements
- Python 3.10+
- Webcam

### Install dependencies:
```bash
pip install opencv-python mediapipe pygame numpy scipy mido
```

---

## 🚀 Run

```bash
cd airpiano
python main.py
```

On first run, AirPiano will automatically generate all 111 sound samples (37 notes × 3 instruments). This takes ~10 seconds.

---

## 🎹 Controls

### Keyboard

| Key | Action |
|-----|--------|
| `R` | Start / Stop Recording |
| `P` | Playback last recording |
| `M` | Export recording as MIDI |
| `J` | Export recording as JSON |
| `1` | Switch to Piano |
| `2` | Switch to Marimba |
| `3` | Switch to Organ |
| `V` | Volume Up |
| `B` | Volume Down |
| `↑` / `↓` | Octave Up / Down |
| `ESC` | Quit |

### Gestures

| Gesture | Action |
|---------|--------|
| Finger tap down | Play note |
| Multiple fingers | Play chord |
| Left hand pinch | Octave down |
| Right hand pinch | Octave up |
| Open palm | Sustain ON |
| Fist | Sustain OFF |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────┐
│                    main.py                       │
│         (Main loop, input handling)              │
├───────────┬───────────┬──────────┬──────────────┤
│           │           │          │              │
│  hand_    │  piano_   │  sound_  │  ui_         │
│  tracker  │  engine   │  engine  │  renderer    │
│  .py      │  .py      │  .py     │  .py         │
│           │           │          │              │
│ MediaPipe │ Key zones │ pygame   │ OpenCV draw  │
│ Hands     │ Press det │ mixer    │ Particles    │
│ Gestures  │ Debounce  │ Poly     │ Glow/HUD    │
│ Velocity  │ Octave    │ Sustain  │ Animation   │
├───────────┴───────────┴──────────┴──────────────┤
│               recorder.py                        │
│     (Record, Playback, MIDI/JSON export)         │
├─────────────────────────────────────────────────┤
│               config.py                          │
│    (Constants, colors, layout, tuning)           │
├─────────────────────────────────────────────────┤
│           generate_sounds.py                     │
│   (Additive synthesis, ADSR, WAV generation)     │
└─────────────────────────────────────────────────┘
```

---

## 📁 File Structure

```
airpiano/
├── main.py                 # Entry point — main loop
├── hand_tracker.py         # MediaPipe hand tracking & gestures
├── piano_engine.py         # Key layout, press detection, debouncing
├── sound_engine.py         # Audio playback, sustain, instruments
├── ui_renderer.py          # All visuals: keys, HUD, particles, glow
├── recorder.py             # Record, playback, MIDI/JSON export
├── config.py               # All constants and settings
├── generate_sounds.py      # Synthetic WAV sample generator
├── assets/
│   └── sounds/
│       ├── piano/          # Piano WAV samples (C3–C6)
│       ├── marimba/        # Marimba WAV samples
│       └── organ/          # Organ WAV samples
└── README.md
```

---

## 🔧 Troubleshooting

### Camera not found
- Ensure your webcam is connected and not being used by another application
- Try changing `cv2.VideoCapture(0)` to `cv2.VideoCapture(1)` in `main.py`

### No sound
- Check that pygame is installed: `pip install pygame`
- Verify sound files exist in `assets/sounds/piano/`
- Run `python generate_sounds.py` manually to regenerate

### Low FPS
- Close other applications using the camera
- Reduce `FRAME_WIDTH` and `FRAME_HEIGHT` in `config.py`
- Lower `MEDIAPIPE_DETECTION_CONF` in `config.py` (try 0.5)
- Disable particle effects by reducing `PARTICLE_COUNT` to 0

### Hands not detected
- Ensure adequate lighting
- Keep hands within the camera frame
- Try adjusting `MEDIAPIPE_DETECTION_CONF` lower (e.g., 0.5)

### Notes trigger too easily / not enough
- Adjust `PRESS_VELOCITY_THRESHOLD` in `config.py` (higher = harder to trigger)
- Adjust `DEBOUNCE_MS` (higher = longer gap between same-key re-triggers)

---

## 📄 License

MIT License — free for personal and educational use.
