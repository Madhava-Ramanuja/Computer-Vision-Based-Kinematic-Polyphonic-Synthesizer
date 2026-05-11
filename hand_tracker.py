"""
AirPiano — Hand Tracker
MediaPipe Hands setup, landmark extraction, gesture detection, and velocity tracking.
"""

import math
import mediapipe as mp
import numpy as np

from config import (
    MEDIAPIPE_MAX_HANDS, MEDIAPIPE_DETECTION_CONF,
    MEDIAPIPE_TRACKING_CONF, PINCH_DISTANCE_PX
)


# MediaPipe hand landmark indices
LANDMARK_WRIST = 0
LANDMARK_THUMB_CMC = 1
LANDMARK_THUMB_MCP = 2
LANDMARK_THUMB_IP = 3
LANDMARK_THUMB_TIP = 4
LANDMARK_INDEX_MCP = 5
LANDMARK_INDEX_PIP = 6
LANDMARK_INDEX_DIP = 7
LANDMARK_INDEX_TIP = 8
LANDMARK_MIDDLE_MCP = 9
LANDMARK_MIDDLE_PIP = 10
LANDMARK_MIDDLE_DIP = 11
LANDMARK_MIDDLE_TIP = 12
LANDMARK_RING_MCP = 13
LANDMARK_RING_PIP = 14
LANDMARK_RING_DIP = 15
LANDMARK_RING_TIP = 16
LANDMARK_PINKY_MCP = 17
LANDMARK_PINKY_PIP = 18
LANDMARK_PINKY_DIP = 19
LANDMARK_PINKY_TIP = 20

# Finger tip and pip indices
FINGER_TIPS = {
    "THUMB": LANDMARK_THUMB_TIP,
    "INDEX": LANDMARK_INDEX_TIP,
    "MIDDLE": LANDMARK_MIDDLE_TIP,
    "RING": LANDMARK_RING_TIP,
    "PINKY": LANDMARK_PINKY_TIP,
}

FINGER_PIPS = {
    "THUMB": LANDMARK_THUMB_IP,
    "INDEX": LANDMARK_INDEX_PIP,
    "MIDDLE": LANDMARK_MIDDLE_PIP,
    "RING": LANDMARK_RING_PIP,
    "PINKY": LANDMARK_PINKY_PIP,
}

# MediaPipe hand connections for drawing skeleton
HAND_CONNECTIONS = mp.solutions.hands.HAND_CONNECTIONS


class HandTracker:
    """Real-time hand tracking and gesture detection using MediaPipe."""

    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=MEDIAPIPE_MAX_HANDS,
            min_detection_confidence=MEDIAPIPE_DETECTION_CONF,
            min_tracking_confidence=MEDIAPIPE_TRACKING_CONF,
        )
        # Store previous frame positions for velocity calculation
        # Key: (hand_index, finger_name) → (px, py)
        self._prev_positions = {}

    def process(self, frame):
        """
        Process a BGR frame and return list of hand data dicts.

        Each hand dict contains:
          - landmarks: list of 21 (x, y, z) normalized coords
          - pixel_landmarks: list of 21 (px, py) pixel coords
          - handedness: "Left" or "Right"
          - fingertips: dict {finger_name: (px, py)}
          - finger_states: dict {finger_name: "up"/"down"}
          - connections: list of (start_idx, end_idx) for skeleton drawing
        """
        import cv2
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)

        hand_list = []

        if results.multi_hand_landmarks is None:
            self._prev_positions.clear()
            return hand_list

        for hand_idx, (hand_landmarks, handedness_info) in enumerate(
            zip(results.multi_hand_landmarks, results.multi_handedness)
        ):
            landmarks = []
            pixel_landmarks = []

            for lm in hand_landmarks.landmark:
                landmarks.append((lm.x, lm.y, lm.z))
                px = int(lm.x * w)
                py = int(lm.y * h)
                pixel_landmarks.append((px, py))

            # Determine handedness (MediaPipe reports mirrored for selfie)
            handedness = handedness_info.classification[0].label  # "Left" or "Right"

            # Extract fingertip pixel positions
            fingertips = {}
            for finger_name, tip_idx in FINGER_TIPS.items():
                fingertips[finger_name] = pixel_landmarks[tip_idx]

            # Determine finger up/down states
            finger_states = self._get_finger_states(pixel_landmarks, handedness)

            hand_data = {
                "landmarks": landmarks,
                "pixel_landmarks": pixel_landmarks,
                "handedness": handedness,
                "fingertips": fingertips,
                "finger_states": finger_states,
                "hand_index": hand_idx,
                "connections": list(HAND_CONNECTIONS),
            }

            hand_list.append(hand_data)

        return hand_list

    def _get_finger_states(self, pixel_landmarks, handedness):
        """
        Determine if each finger is "up" or "down".
        Uses Y-coordinate comparison between tip and PIP joint.
        For thumb, uses X-coordinate comparison.
        """
        states = {}

        for finger_name in ["INDEX", "MIDDLE", "RING", "PINKY"]:
            tip_idx = FINGER_TIPS[finger_name]
            pip_idx = FINGER_PIPS[finger_name]
            tip_y = pixel_landmarks[tip_idx][1]
            pip_y = pixel_landmarks[pip_idx][1]
            # Tip above PIP (lower Y in image coords) = finger up
            states[finger_name] = "up" if tip_y < pip_y else "down"

        # Thumb: compare X position of tip vs IP joint
        thumb_tip_x = pixel_landmarks[LANDMARK_THUMB_TIP][0]
        thumb_ip_x = pixel_landmarks[LANDMARK_THUMB_IP][0]
        if handedness == "Right":
            # Right hand: thumb tip to the left of IP = up (in mirrored view)
            states["THUMB"] = "up" if thumb_tip_x < thumb_ip_x else "down"
        else:
            states["THUMB"] = "up" if thumb_tip_x > thumb_ip_x else "down"

        return states

    def is_pinch(self, hand):
        """Check if thumb and index fingertips are close together (pinch gesture)."""
        thumb_pos = hand["fingertips"]["THUMB"]
        index_pos = hand["fingertips"]["INDEX"]
        distance = math.sqrt(
            (thumb_pos[0] - index_pos[0]) ** 2 +
            (thumb_pos[1] - index_pos[1]) ** 2
        )
        return distance < PINCH_DISTANCE_PX

    def is_open_palm(self, hand):
        """Check if all 5 fingers are up (open palm gesture)."""
        return all(state == "up" for state in hand["finger_states"].values())

    def is_fist(self, hand):
        """Check if all 5 fingers are down (fist gesture)."""
        return all(state == "down" for state in hand["finger_states"].values())

    def get_fingertip_velocity(self, hand_index, finger_name, current_pos):
        """
        Calculate fingertip velocity (dx, dy) from previous frame.
        Returns (0, 0) if no previous position exists.
        """
        key = (hand_index, finger_name)
        prev_pos = self._prev_positions.get(key, None)
        self._prev_positions[key] = current_pos

        if prev_pos is None:
            return (0, 0)

        dx = current_pos[0] - prev_pos[0]
        dy = current_pos[1] - prev_pos[1]
        return (dx, dy)

    def release(self):
        """Release MediaPipe resources."""
        self.hands.close()
