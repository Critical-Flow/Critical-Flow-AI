# src/service/frame_analysis_service.py

import time

import cv2
import numpy as np

from src.core.config import LOOP_INTERVAL
from src.domain.enums import FocusState
from src.domain.session_data import SessionData
from src.engine.interface import IAnalysisEngine

"""
HTTP 로 전송된 프레임 분석 서비스 (FrameAnalysisService 클래스)

WebcamAnalysisService (로컬 웹캠 루프) 를 EC2 환경에 맞게 대체한 서비스.
프론트엔드가 웹캠으로 캡처한 JPEG/PNG 프레임을 HTTP 로 수신해 분석한다.
"""


class FrameAnalysisService:
    """
    프론트엔드에서 HTTP 로 전송된 프레임을 분석하는 서비스.

    WebcamAnalysisService(로컬 웹캠 루프)를 대체.
    EC2 환경에서 웹캠 없이 프론트엔드가 캡처한 프레임을 직접 수신해 분석.

    [SRP] 프레임 디코딩 + 분석 엔진 위임 + 세션 데이터 누적만 담당.
    [DIP] 분석 로직은 IAnalysisEngine 에 위임.
    """

    def __init__(self, engine: IAnalysisEngine, data: SessionData) -> None:
        self._engine      = engine
        self._data        = data
        self._last_tick   = time.time()
        self._last_state  = FocusState.GOOD   # ESP32 폴링용 현재 상태 캐시

    def process_frame(self, frame_bytes: bytes) -> dict:
        """
        JPEG/PNG 바이트를 디코딩하여 집중 상태를 분석한다.
        LOOP_INTERVAL(1초) 주기로 SessionData 에 상태를 누적한다.

        Args:
            frame_bytes: 프론트엔드가 전송한 이미지 바이트 (JPEG 또는 PNG)

        Returns:
            {
              "focusState":    "GOOD" | "DROWSY" | "ABSENT",
              "elapsed":       float,   # 위반 지속 시간 (초)
              "isTimerActive": bool,    # 위반 타이머 진행 중 여부
            }

        Raises:
            ValueError: 이미지 디코딩에 실패한 경우
        """
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            raise ValueError("이미지 디코딩 실패 — 유효한 JPEG/PNG 파일을 전송하세요.")

        state: FocusState = self._engine.analyze(frame)
        self._last_state  = state   # ESP32 폴링용 캐시 갱신

        # LOOP_INTERVAL(1초) 주기로 세션 누적 데이터 갱신
        now = time.time()
        if now - self._last_tick >= LOOP_INTERVAL:
            self._data.accumulate(state)
            self._last_tick = now

        info = self._engine.get_state_info()

        return {
            "focusState":    state.value,
            "elapsed":       round(info["elapsed"], 2),
            "isTimerActive": info["is_timer_active"],
        }

    def get_current_state(self) -> FocusState:
        """ESP32 폴링용 — 마지막으로 분석된 집중 상태를 반환."""
        return self._last_state

    def release(self) -> None:
        """분석 엔진 리소스 해제."""
        self._engine.release()
