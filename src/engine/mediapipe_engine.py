# src/engine/mediapipe_engine.py

import cv2
import numpy as np

from src.analysis.face_analyzer import FaceAnalyzer
from src.core.config import (
    DISTRACTION_TIMEOUT,
    DROWSY_CLOSED_SECONDS,
    DROWSY_EAR_THRESHOLD,
    DROWSY_RECOVERY_CLOSED_RATIO,
    DROWSY_RECOVERY_COOLDOWN_SECONDS,
    DROWSY_RECOVERY_WINDOW_SECONDS,
    EAR_THRESHOLD,
    FACE_LOST_RESET_SECONDS,
    FOCUS_EVENTS_URL,
    LEFT_EYE,
    PERCLOS_THRESHOLD,
    PERCLOS_WINDOW_SECONDS,
    RIGHT_EYE,
)
from src.detection.face_detector import FaceDetector
from src.domain.enums import FocusState
from src.engine.interface import IAnalysisEngine
from src.repository.focus_event_client import FocusEventClient
from src.service.state_manager import StateManager
from src.services.drowsiness_manager import DrowsinessManager


class RealMediaPipeEngine(IAnalysisEngine):
    """
    MediaPipe Face Mesh + EAR/PERCLOS 기반 실제 집중도 분석 엔진.

    파이프라인 흐름:
      BGR 프레임
        → ① cv2 전처리 (BGR → RGB)
        → ② FaceDetector      : MediaPipe Face Mesh 로 랜드마크 추출
        → ③ FaceAnalyzer      : EAR 계산으로 '눈 감음 / 이탈 / 정상' 판정
        → ④ DrowsinessManager : 연속 눈감김 / PERCLOS 로 졸음 확정
        → ⑤ StateManager      : DISTRACTION_TIMEOUT(3초) 이상 지속 시 상태 확정
        → FocusState 반환
    """

    _LABEL_MAP: dict[str, FocusState] = {
        "좋음":    FocusState.GOOD,
        "눈 감음": FocusState.DROWSY,
        "졸음":    FocusState.DROWSY,   # PERCLOS/연속 눈감김 확정 상태
        "이탈":    FocusState.ABSENT,
    }

    def __init__(self, session_id: int) -> None:
        self._detector  = FaceDetector()
        self._analyzer  = FaceAnalyzer(EAR_THRESHOLD)

        _event_client   = FocusEventClient(FOCUS_EVENTS_URL, session_id)

        self._state_mgr = StateManager(
            timeout      = DISTRACTION_TIMEOUT,
            event_client = _event_client,
        )

        self._drowsiness_mgr = DrowsinessManager(
            ear_threshold              = DROWSY_EAR_THRESHOLD,
            closed_seconds             = DROWSY_CLOSED_SECONDS,
            perclos_window_seconds     = PERCLOS_WINDOW_SECONDS,
            perclos_threshold          = PERCLOS_THRESHOLD,
            recovery_window_seconds    = DROWSY_RECOVERY_WINDOW_SECONDS,
            recovery_closed_ratio      = DROWSY_RECOVERY_CLOSED_RATIO,
            recovery_cooldown_seconds  = DROWSY_RECOVERY_COOLDOWN_SECONDS,
        )

        self._left_eye  = LEFT_EYE
        self._right_eye = RIGHT_EYE

    def analyze(self, frame: np.ndarray) -> FocusState:
        """
        BGR 프레임 1장을 분석하여 확정된 집중 상태를 반환.

        - 얼굴 미감지  → "이탈"   → ABSENT  (3초 지속 시 확정)
        - 눈 감음 3초 연속 또는 30초 중 20% 이상 → "졸음" → DROWSY
        - EAR < 0.18   → "눈 감음" → DROWSY  (3초 지속 시 확정)
        - 정상          → "좋음"   → GOOD
        """
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        landmarks = self._detector.process(frame_rgb)

        face_detected = bool(landmarks)

        violation = self._analyzer.get_frame_violation(
            landmarks, self._left_eye, self._right_eye
        )

        drowsy_info = {
            "is_drowsy": False,
            "reason":    "NORMAL",
        }

        if not face_detected:
            # 얼굴 미검출 → DrowsinessManager 기록 처리 + "이탈" 전달
            drowsy_info = self._drowsiness_mgr.update_face_lost(FACE_LOST_RESET_SECONDS)
            violation = "이탈"
        else:
            avg_ear = self._analyzer.get_avg_ear(
                landmarks, self._left_eye, self._right_eye
            )
            if avg_ear is not None:
                drowsy_info = self._drowsiness_mgr.update(avg_ear)

        # PERCLOS 또는 연속 눈감김으로 졸음 확정 시 violation 덮어쓰기
        if drowsy_info["is_drowsy"]:
            violation = "졸음"

        confirmed_label = self._state_mgr.update(violation)

        return self._LABEL_MAP.get(confirmed_label, FocusState.GOOD)

    def get_state_info(self) -> dict:
        """StateManager 의 현재 상태 정보를 UIManager 렌더링 형식으로 반환."""
        return self._state_mgr.get_current_info()

    def release(self) -> None:
        """MediaPipe Face Mesh 리소스 해제."""
        self._detector.close()
