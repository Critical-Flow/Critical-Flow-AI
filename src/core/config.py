# src/core/config.py
# 애플리케이션 전역 설정 상수

# ── API 서버 설정 ──────────────────────────────────────────────
# {sessionId} 는 BackendClient 에서 치환됩니다.
BACKEND_URL      = "http://app:8080/api/v1/sessions/{sessionId}/vision-result"
FOCUS_EVENTS_URL = "http://app:8080/api/v1/sessions/{userId}/focus-events"
LOOP_INTERVAL    = 1.0   # 상태 누적 주기 (초)

# ── MediaPipe Face Mesh 랜드마크 인덱스 ───────────────────────
LEFT_EYE  = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
RIGHT_EYE = [33,  7,   163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]

# ── 임계값 및 타임아웃 ────────────────────────────────────────
EAR_THRESHOLD       = 0.2
DISTRACTION_TIMEOUT = 3.0   # 위반 상태가 이 시간(초) 이상 지속되어야 확정

# ── UI ───────────────────────────────────────────────────────
WINDOW_NAME        = "Critical Flow AI"
COLOR_CONCENTRATED = (0, 255, 0)   # 집중: 초록
COLOR_DISTRACTED   = (0, 0, 255)   # 분산: 빨강
FONT_FACE          = 0             # cv2.FONT_HERSHEY_SIMPLEX

