import threading
import time

import cv2

from src.core.config import LOOP_INTERVAL, WINDOW_NAME
from src.domain.session_data import SessionData
from src.engine.interface import IAnalysisEngine
from src.ui.cv_window import UIManager


class WebcamAnalysisService:
    """
    웹캠 분석 루프

    웹캠을 열고 매 프레임을 IAnalysisEngine 에 위임하며,
    LOOP_INTERVAL 주기로 SessionData 에 상태를 누적한다.
    UIManager 를 통해 분석 상태를 웹캠 화면에 실시간으로 오버레이한다.

    [SRP] 웹캠 생명주기 + 분석 루프 실행 + 화면 렌더링 조율만 담당.
    [DIP] 분석 로직은 IAnalysisEngine, 렌더링은 UIManager 에 각각 위임.

    [중요] run() 은 블로킹 함수이므로 asyncio run_in_executor (별도 OS 스레드) 에서 실행.
           stop_event 로 API 레이어 ↔ 스레드 간 종료 신호를 안전하게 전달.
    """

    def __init__(self, engine: IAnalysisEngine, data: SessionData) -> None:
        self._engine     = engine
        self._data       = data
        self._ui         = UIManager(WINDOW_NAME)
        self._stop_event = threading.Event()

    def request_stop(self) -> None:
        """API 레이어에서 호출 → 분석 루프에 종료 신호 전달 (논블로킹)."""
        self._stop_event.set()

    def run(self) -> None:
        """블로킹 루프 본체 — run_in_executor 로 별도 OS 스레드에서 실행됨."""
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[ERROR] 웹캠을 열 수 없습니다.")
            return

        print("[INFO] 웹캠 분석 루프 시작.")
        last_tick = time.time()

        try:
            while not self._stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    print("[WARN] 프레임 읽기 실패 — 루프 종료.")
                    break

                # ── 전처리 + 분석 ──────────────────────────────
                frame = cv2.flip(frame, 1)
                state = self._engine.analyze(frame)

                # ── UI 렌더링: 상태 오버레이 → 화면 출력 ────────
                self._ui.render(frame, self._engine.get_state_info())

                # ── 1초마다 세션 데이터 누적 ──────────────────────
                now = time.time()
                if now - last_tick >= LOOP_INTERVAL:
                    self._data.accumulate(state)
                    last_tick = now

        finally:
            cap.release()
            self._engine.release()
            self._ui.close()
            print("[INFO] 웹캠 분석 루프 종료.")
