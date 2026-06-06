# src/core/config.py
# 애플리케이션 전역 설정 상수

# ── API 서버 설정 ──────────────────────────────────────────────
# {sessionId} 는 BackendClient 에서 치환됩니다.
BACKEND_URL = "http://app:8080/api/v1/sessions/{sessionId}/vision-result"
FOCUS_EVENTS_URL = "http://app:8080/api/v1/sessions/{userId}/focus-events"

# 상태 누적 주기, 초
LOOP_INTERVAL = 1.0


# ── MediaPipe Face Mesh 랜드마크 인덱스 ───────────────────────
LEFT_EYE = [
    362, 382, 381, 380, 374, 373, 390, 249,
    263, 466, 388, 387, 386, 385, 384, 398,
]

RIGHT_EYE = [
    33, 7, 163, 144, 145, 153, 154, 155,
    133, 173, 157, 158, 159, 160, 161, 246,
]


# ── 기존 집중도 판정 임계값 ───────────────────────────────────
EAR_THRESHOLD = 0.18

# 위반 상태가 이 시간 이상 지속되어야 확정
DISTRACTION_TIMEOUT = 3.0


# ── Drowsiness / PERCLOS 설정 ───────────────────────────────
# EAR 값이 이 값보다 작으면 눈 감김으로 판단
DROWSY_EAR_THRESHOLD = 0.18

# EAR < threshold 상태가 몇 초 이상 연속 유지되면 졸음으로 판단
DROWSY_CLOSED_SECONDS = 3.0

# PERCLOS 계산 창
PERCLOS_WINDOW_SECONDS = 30.0

# 최근 30초 동안 눈 감김 비율이 20% 이상이면 졸음으로 판단
PERCLOS_THRESHOLD = 0.20

# 얼굴이 안 잡힌 상태가 몇 초 이상 지속되면 자리비움으로 보고 졸음 기록 초기화
FACE_LOST_RESET_SECONDS = 5.0

# 졸음 복귀 판정용 짧은 창
DROWSY_RECOVERY_WINDOW_SECONDS = 10.0
DROWSY_RECOVERY_CLOSED_RATIO = 0.10

# 복귀 직후 PERCLOS 재진입 방지 쿨다운
DROWSY_RECOVERY_COOLDOWN_SECONDS = 10.0


# ── UI ───────────────────────────────────────────────────────
WINDOW_NAME = "Critical Flow AI"

COLOR_CONCENTRATED = (0, 255, 0)  # 집중: 초록
COLOR_DISTRACTED = (0, 0, 255)    # 분산: 빨강

FONT_FACE = 0  # cv2.FONT_HERSHEY_SIMPLEX