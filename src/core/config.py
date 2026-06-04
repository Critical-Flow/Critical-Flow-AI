# src/core/config.py
# 애플리케이션 전역 설정 상수

# ── API 서버 설정 ──────────────────────────────────────────────
BACKEND_URL      = "http://localhost:8080/api/v1/sessions/end"
FOCUS_EVENTS_URL = "https://api.aice-edu.site/api/v1/sessions/{userId}/focus-events"
LOOP_INTERVAL    = 1.0   # 상태 누적 주기 (초)

# ── ESP32 IoT 설정 ──────────────────────────────────────────────
# ESP32 의 실제 IP 주소로 변경하세요 (공유기 DHCP 확인 또는 고정 IP 권장)
ESP32_URL        = "http://192.168.0.50/alert"   # ESP32 HTTP 엔드포인트
ESP32_ENABLED    = True                           # False 로 바꾸면 ESP32 전송 비활성화

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

