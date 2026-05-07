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
# HEAD_POSE_THRESHOLD: 얼굴 숙임 감지 임계값. 
# 0.12는 너무 민감하고, 0.20은 너무 둔감할 수 있습니다.
# 보통 0.15 ~ 0.17 사이가 적당하며, 현재는 0.16으로 설정했습니다.
HEAD_POSE_THRESHOLD = 0.16
# DISTRACTION_TIMEOUT: 위반 상태가 몇 초간 지속되어야 '분산' 상태로 판정할지 설정 (초 단위)
DISTRACTION_TIMEOUT = 3.0

# UI Settings
WINDOW_NAME = 'Concentration Tracker'
FONT_FACE = 0 # cv2.FONT_HERSHEY_SIMPLEX
COLOR_CONCENTRATED = (0, 255, 0)
COLOR_DISTRACTED = (0, 0, 255)
LOG_FILE = "status_log.txt"
