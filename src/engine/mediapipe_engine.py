import cv2
import numpy as np

from src.analysis.face_analyzer import FaceAnalyzer
from src.core.config import (
    DISTRACTION_TIMEOUT,
    EAR_THRESHOLD,
    FOCUS_EVENTS_URL,
    LEFT_EYE,
    RIGHT_EYE,
)
from src.detection.face_detector import FaceDetector
from src.domain.enums import FocusState
from src.engine.interface import IAnalysisEngine
from src.repository.focus_event_client import FocusEventClient
from src.services.state_manager import StateManager


class RealMediaPipeEngine(IAnalysisEngine):
    """
    MediaPipe Face Mesh + EAR(Eye Aspect Ratio) 기반 실제 집중도 분석 엔진.

    파이프라인 흐름:
      BGR 프레임
        → ① cv2 전처리 (BGR → RGB)
        → ② FaceDetector  : MediaPipe Face Mesh 로 랜드마크 추출
        → ③ FaceAnalyzer  : EAR 계산으로 '눈 감음 / 이탈 / 정상' 판정
        → ④ StateManager  : DISTRACTION_TIMEOUT(3초) 이상 지속 시 상태 확정
        → FocusState 반환
    """

    _LABEL_MAP: dict[str, FocusState] = {
        "좋음":    FocusState.GOOD,
        "눈 감음": FocusState.DROWSY,
        "이탈":    FocusState.ABSENT,
    }

    def __init__(self, user_id: int) -> None:
        self._detector  = FaceDetector()
        self._analyzer  = FaceAnalyzer(EAR_THRESHOLD)
        _event_client   = FocusEventClient(FOCUS_EVENTS_URL, user_id)
        self._state_mgr = StateManager(DISTRACTION_TIMEOUT, _event_client)
        self._left_eye  = LEFT_EYE
        self._right_eye = RIGHT_EYE

    def analyze(self, frame: np.ndarray) -> FocusState:
        """
        BGR 프레임 1장을 분석하여 확정된 집중 상태를 반환.

        - 얼굴 미감지          → "이탈"   → ABSENT  (3초 지속 시 확정)
        - EAR < 0.2 (눈 감음)  → "눈 감음" → DROWSY  (3초 지속 시 확정)
        - 정상                 → "좋음"   → GOOD
        """
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        landmarks = self._detector.process(frame_rgb)

        violation = self._analyzer.get_frame_violation(
            landmarks, self._left_eye, self._right_eye
        )

        confirmed_label = self._state_mgr.update(violation)

        return self._LABEL_MAP[confirmed_label]

    def get_state_info(self) -> dict:
        """StateManager 의 현재 상태 정보를 UIManager 렌더링 형식으로 반환."""
        return self._state_mgr.get_current_info()

    def release(self) -> None:
        """MediaPipe Face Mesh 리소스 해제."""
        self._detector.close()
