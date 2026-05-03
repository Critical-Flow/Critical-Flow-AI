# src/core/config.py
# Configuration constants for the Concentration Tracker

"""
설정 값을 관리
"""

# MediaPipe Face Mesh indices
LEFT_EYE = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
RIGHT_EYE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]

# Thresholds and Timeouts
EAR_THRESHOLD = 0.2
HEAD_POSE_THRESHOLD = 0.12
DISTRACTION_TIMEOUT = 5.0

# UI Settings
WINDOW_NAME = 'Concentration Tracker'
FONT_FACE = 0 # cv2.FONT_HERSHEY_SIMPLEX
COLOR_CONCENTRATED = (0, 255, 0)
COLOR_DISTRACTED = (0, 0, 255)
LOG_FILE = "status_log.txt"
