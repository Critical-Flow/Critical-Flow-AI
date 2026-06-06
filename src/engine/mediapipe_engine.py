# src/engine/mediapipe_engine.py

import cv2
import numpy as np

from src.analysis.face_analyzer import FaceAnalyzer
from src.core.config import (
    DISTRACTION_TIMEOUT,
    EAR_THRESHOLD,
    FOCUS_EVENTS_URL,
    LEFT_EYE,
    RIGHT_EYE,
    DROWSY_EAR_THRESHOLD,
    DROWSY_CLOSED_SECONDS,
    PERCLOS_WINDOW_SECONDS,
    PERCLOS_THRESHOLD,
    FACE_LOST_RESET_SECONDS,
    DROWSY_RECOVERY_WINDOW_SECONDS,
    DROWSY_RECOVERY_CLOSED_RATIO,
    DROWSY_RECOVERY_COOLDOWN_SECONDS,
)
from src.detection.face_detector import FaceDetector
from src.domain.enums import FocusState
from src.engine.interface import IAnalysisEngine
from src.repository.focus_event_client import FocusEventClient
from src.services.drowsiness_manager import DrowsinessManager
from src.services.state_manager import StateManager


class RealMediaPipeEngine(IAnalysisEngine):
    """
    MediaPipe Face Mesh + EAR/PERCLOS 기반 실제 집중도 분석 엔진.

    파이프라인:
    BGR frame
    → RGB 변환
    → MediaPipe Face Mesh landmark 추출
    → EAR 계산
    → DrowsinessManager로 연속 눈감김/PERCLOS 판정
    → StateManager로 DISTRACTION_TIMEOUT 이상 지속 여부 확정
    → FocusState 반환
    """

    _LABEL_MAP: dict[str, FocusState] = {
        "좋음": FocusState.GOOD,
        "눈 감음": FocusState.DROWSY,
        "졸음": FocusState.DROWSY,
        "이탈": FocusState.ABSENT,
    }

    def __init__(self, user_id: int) -> None:
        self._detector = FaceDetector()
        self._analyzer = FaceAnalyzer(EAR_THRESHOLD)

        event_client = FocusEventClient(FOCUS_EVENTS_URL, user_id)
        self._state_mgr = StateManager(DISTRACTION_TIMEOUT, event_client)

        self._drowsiness_mgr = DrowsinessManager(
            ear_threshold=DROWSY_EAR_THRESHOLD,
            closed_seconds=DROWSY_CLOSED_SECONDS,
            perclos_window_seconds=PERCLOS_WINDOW_SECONDS,
            perclos_threshold=PERCLOS_THRESHOLD,
            recovery_window_seconds=DROWSY_RECOVERY_WINDOW_SECONDS,
            recovery_closed_ratio=DROWSY_RECOVERY_CLOSED_RATIO,
            recovery_cooldown_seconds=DROWSY_RECOVERY_COOLDOWN_SECONDS,
        )

        self._left_eye = LEFT_EYE
        self._right_eye = RIGHT_EYE

    def analyze(self, frame: np.ndarray) -> FocusState:
        """
        BGR 프레임 1장을 분석하여 확정된 집중 상태를 반환한다.

        반환:
        - FocusState.GOOD
        - FocusState.DROWSY
        - FocusState.ABSENT
        """
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        landmarks = self._detector.process(frame_rgb)

        face_detected = bool(landmarks)

        violation = self._analyzer.get_frame_violation(
            landmarks,
            self._left_eye,
            self._right_eye,
        )

        drowsy_info = {
            "is_drowsy": False,
            "reason": "NORMAL",
            "ear": None,
            "closed": False,
            "closed_duration": 0.0,
            "perclos": 0.0,
            "elapsed": 0.0,
            "recovery_closed_ratio": 0.0,
        }

        if not face_detected:
            drowsy_info = self._drowsiness_mgr.update_face_lost(
                FACE_LOST_RESET_SECONDS
            )

            # 얼굴 미검출은 PERCLOS에 추가하지 않고,
            # StateManager에 "이탈"만 넘겨 timeout 이후 ABSENT로 확정시킨다.
            violation = "이탈"

        else:
            avg_ear = self._analyzer.get_avg_ear(
                landmarks,
                self._left_eye,
                self._right_eye,
            )

            if avg_ear is not None:
                drowsy_info = self._drowsiness_mgr.update(avg_ear)

        # 연속 눈감김 또는 PERCLOS로 졸음 상태면 기존 violation을 덮어쓴다.
        if drowsy_info["is_drowsy"]:
            violation = "졸음"

        confirmed_label = self._state_mgr.update(violation)

        return self._LABEL_MAP.get(confirmed_label, FocusState.GOOD)

    def get_state_info(self) -> dict:
        """
        StateManager의 현재 상태 정보를 UIManager 렌더링 형식으로 반환.
        """
        return self._state_mgr.get_current_info()

    def release(self) -> None:
        """
        MediaPipe Face Mesh 리소스 해제.
        """
        self._detector.close()