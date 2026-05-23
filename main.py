"""
Critical Flow AI  —  학습 집중도 실시간 분석 서버
==================================================
실행: python main.py

SOLID 아키텍처 레이어 구조:
  ┌─────────────────────────────────────────────────────────────┐
  │  [API Layer]  FastAPI Endpoints  (/start · /stop)           │
  │       │  위임                                               │
  │  [Orchestration]  SessionOrchestrator                       │
  │       │  SRP – 세션 생명주기 조율만 담당                    │
  │       ├─ [Domain]  SessionData                              │
  │       │       SRP – 순수 상태 데이터 컨테이너               │
  │       ├─ [Service]  WebcamAnalysisService                   │
  │       │       SRP – 웹캠 루프 + 프레임 분석 위임            │
  │       │       └─ IAnalysisEngine  ◄──── DIP / OCP          │
  │       │             ├─ SimulatedAnalysisEngine  (기본)       │
  │       │             └─ RealMediaPipeEngine      (교체 대상) │
  │       └─ [Service]  SessionReportService                    │
  │               SRP – 통계 정산 + 외부 백엔드 전송            │
  └─────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import asyncio
import random
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

import cv2
import httpx
import numpy as np
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# ==============================================================
# ① 설정 (Configuration)
# ==============================================================
BACKEND_URL   = "http://localhost:8080/api/v1/sessions/789/end"
SESSION_ID    = 789
USER_ID       = 123
LOOP_INTERVAL = 1.0   # 상태 누적 주기 (초)


# ==============================================================
# ② 도메인 모델 (Domain Models)
# ==============================================================
class FocusState(str, Enum):
    GOOD   = "GOOD"
    DROWSY = "DROWSY"
    ABSENT = "ABSENT"


class SessionResult(BaseModel):
    """백엔드 전송용 최종 통계 스키마."""
    sessionId:         int
    userId:            int
    totalStudySeconds: int
    goodFocusSeconds:  int
    drowsySeconds:     int
    absentSeconds:     int
    drowsyCount:       int
    absentCount:       int


# ==============================================================
# ③ 세션 데이터  (SRP — 순수 상태 컨테이너 + 누적 책임)
# ==============================================================
@dataclass
class SessionData:
    """
    웹캠 분석 스레드와 API 레이어가 공유하는 세션 누적 데이터.

    [Thread-Safety]
    Python GIL 하에서 int += 1 은 단일 바이트코드 연산이므로
    별도 Lock 없이 안전하게 공유 가능.
    """
    drowsy_seconds: int                    = 0
    absent_seconds: int                    = 0
    drowsy_count:   int                    = 0
    absent_count:   int                    = 0
    prev_state:     Optional[FocusState]   = field(default=None)

    def accumulate(self, state: FocusState) -> None:
        """1초 tick마다 호출 — 상태별 누적 시간 및 진입 횟수 갱신."""
        if state == FocusState.DROWSY:
            self.drowsy_seconds += 1
            if self.prev_state != FocusState.DROWSY:   # 졸음 상태 새로 진입
                self.drowsy_count += 1

        elif state == FocusState.ABSENT:
            self.absent_seconds += 1
            if self.prev_state != FocusState.ABSENT:   # 자리 이탈 새로 진입
                self.absent_count += 1

        self.prev_state = state


# ==============================================================
# ④ 분석 엔진 추상 인터페이스  (DIP / OCP / ISP)
#
#   [OCP]  IAnalysisEngine 구현체만 추가하면 기존 코드 수정 불필요
#   [DIP]  상위 레이어(WebcamAnalysisService)가 추상에만 의존
#   [ISP]  클라이언트가 쓰지 않는 메서드를 강제하지 않도록 2개로 최소화
# ==============================================================
class IAnalysisEngine(ABC):
    """프레임 1장 → 집중 상태 반환. 구현체 교체로 AI 모델 전환 가능."""

    @abstractmethod
    def analyze(self, frame: np.ndarray) -> FocusState:
        """BGR 프레임 1장을 분석하여 집중 상태를 반환."""
        ...

    @abstractmethod
    def release(self) -> None:
        """보유 중인 모델/파일 핸들 등 리소스를 해제."""
        ...


# ==============================================================
# ⑤-A  시뮬레이션 엔진  (기본 구현체 — 실제 카메라 불필요)
# ==============================================================
class SimulatedAnalysisEngine(IAnalysisEngine):
    """
    프레임을 사용하지 않고 가중치 랜덤으로 집중 상태를 시뮬레이션.
    RealMediaPipeEngine 과 완전히 동일한 인터페이스를 구현 (LSP).
    """

    def analyze(self, frame: np.ndarray) -> FocusState:
        return random.choices(
            population=[FocusState.GOOD, FocusState.DROWSY, FocusState.ABSENT],
            weights=[70, 20, 10],
            k=1,
        )[0]

    def release(self) -> None:
        pass   # 해제할 리소스 없음


# ==============================================================
# ⑤-B  실제 MediaPipe 엔진  (OCP — 교체용 구현체)
#
#   아래 TODO 주석 블록을 활성화하면 실제 AI 분석으로 전환됩니다.
#   SessionOrchestrator 를 포함한 다른 코드는 한 줄도 변경 불필요.
# ==============================================================
class RealMediaPipeEngine(IAnalysisEngine):
    """
    MediaPipe Face Mesh + EAR(Eye Aspect Ratio) 기반 실제 집중도 엔진.

    [사용 방법]
    1. __init__ 의 TODO 블록 주석 해제
    2. SessionOrchestrator 생성 시 engine_factory=RealMediaPipeEngine 으로 변경
    """

    # StateManager 한국어 레이블 → FocusState 매핑
    _LABEL_MAP: dict[str, FocusState] = {
        "좋음":   FocusState.GOOD,
        "눈 감음": FocusState.DROWSY,
        "이탈":   FocusState.ABSENT,
    }

    def __init__(self) -> None:
        # ── TODO: AI 모델 초기화 ──────────────────────────────
        # from src.detection.face_detector import FaceDetector
        # from src.analysis.face_analyzer  import FaceAnalyzer
        # from src.services.state_manager  import StateManager
        # from src.core.config import (
        #     EAR_THRESHOLD, DISTRACTION_TIMEOUT,
        #     LEFT_EYE, RIGHT_EYE, LOG_FILE,
        # )
        # self._detector  = FaceDetector()
        # self._analyzer  = FaceAnalyzer(EAR_THRESHOLD)
        # self._state_mgr = StateManager(DISTRACTION_TIMEOUT, LOG_FILE)
        # self._left_eye  = LEFT_EYE
        # self._right_eye = RIGHT_EYE
        # ─────────────────────────────────────────────────────
        raise NotImplementedError(
            "RealMediaPipeEngine: __init__ 의 TODO 블록을 먼저 구현해 주세요."
        )

    def analyze(self, frame: np.ndarray) -> FocusState:
        # ── TODO: ① 프레임 전처리 ─────────────────────────────
        # frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # ── TODO: ② 랜드마크 감지 (MediaPipe Face Mesh) ───────
        # landmarks = self._detector.process(frame_rgb)

        # ── TODO: ③ EAR 기반 위반 판정 ───────────────────────
        # violation = self._analyzer.get_frame_violation(
        #     landmarks, self._left_eye, self._right_eye
        # )

        # ── TODO: ④ 상태 확정 (DISTRACTION_TIMEOUT 적용) ─────
        # confirmed_label = self._state_mgr.update(violation)
        # return self._LABEL_MAP[confirmed_label]
        # ─────────────────────────────────────────────────────
        raise NotImplementedError

    def release(self) -> None:
        # ── TODO: 리소스 해제 ────────────────────────────────
        # self._detector.close()
        # ─────────────────────────────────────────────────────
        pass


# ==============================================================
# ⑥ 웹캠 분석 서비스  (SRP — 카메라 생명주기 + 분석 루프만 담당)
# ==============================================================
class WebcamAnalysisService:
    """
    웹캠을 열고 매 프레임을 IAnalysisEngine 에 위임하며,
    LOOP_INTERVAL 주기로 SessionData 에 상태를 누적한다.

    [중요] run() 은 블로킹 함수 → asyncio executor(별도 OS 스레드)에서 실행.
    stop_event 로 API 레이어와 스레드 간 종료 신호를 안전하게 전달.
    """

    def __init__(self, engine: IAnalysisEngine, data: SessionData) -> None:
        self._engine     = engine
        self._data       = data
        self._stop_event = threading.Event()

    def request_stop(self) -> None:
        """API 레이어 → 분석 루프에 종료 신호 전달 (논블로킹)."""
        self._stop_event.set()

    def run(self) -> None:
        """블로킹 루프 본체 — run_in_executor 로 스레드에서 실행됨."""
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

                # ── 프레임 좌우 반전 (거울 모드) ─────────────
                frame = cv2.flip(frame, 1)

                # ── 엔진에 분석 위임 (DIP 적용 지점) ─────────
                state = self._engine.analyze(frame)

                # ── 1초마다 세션 데이터 누적 ──────────────────
                now = time.time()
                if now - last_tick >= LOOP_INTERVAL:
                    self._data.accumulate(state)
                    last_tick = now

        finally:
            cap.release()
            self._engine.release()
            print("[INFO] 웹캠 분석 루프 종료.")


# ==============================================================
# ⑦ 세션 리포트 서비스  (SRP — 통계 정산 + 외부 전송만 담당)
# ==============================================================
class SessionReportService:
    """최종 통계 계산 및 Spring Boot 백엔드 비동기 전송 책임."""

    def __init__(self, backend_url: str, session_id: int, user_id: int) -> None:
        self._backend_url = backend_url
        self._session_id  = session_id
        self._user_id     = user_id

    def calculate(
        self,
        data:       SessionData,
        start_time: float,
        end_time:   float,
    ) -> SessionResult:
        """
        [보정 로직 — Data Integrity]
        totalStudySeconds  = 종료 시각 - 시작 시각  (타임스탬프 기준)
        goodFocusSeconds   = total - (drowsy + absent)  ← 역산으로 오차 흡수

        drowsy + absent > total 인 경우 (tick 타이밍 오차):
          → 비율에 따라 비례 스케일 다운 후 역산
        """
        total  = int(end_time - start_time)
        drowsy = data.drowsy_seconds
        absent = data.absent_seconds

        combined = drowsy + absent
        if combined > total:
            scale  = total / combined
            drowsy = int(drowsy * scale)
            absent = total - drowsy          # 나머지를 absent 에 배정

        good = total - (drowsy + absent)     # goodFocusSeconds 역산

        return SessionResult(
            sessionId         = self._session_id,
            userId            = self._user_id,
            totalStudySeconds = total,
            goodFocusSeconds  = good,
            drowsySeconds     = drowsy,
            absentSeconds     = absent,
            drowsyCount       = data.drowsy_count,
            absentCount       = data.absent_count,
        )

    async def send(self, result: SessionResult) -> str:
        """httpx 비동기 클라이언트로 백엔드에 POST 전송."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self._backend_url,
                    json=result.model_dump(),
                    timeout=10.0,
                )
                response.raise_for_status()
                return "success"

            except httpx.HTTPStatusError as e:
                return f"backend_error ({e.response.status_code})"
            except httpx.RequestError as e:
                return f"connection_error: {e}"


# ==============================================================
# ⑧ 세션 오케스트레이터  (SRP — 세션 생명주기 조율만 담당)
# ==============================================================
class SessionOrchestrator:
    """
    /start·/stop 요청을 받아 WebcamAnalysisService 와
    SessionReportService 를 조율하는 얇은 레이어.

    [engine_factory]
    매 세션마다 새 엔진 인스턴스를 생성하는 callable.
    현재: SimulatedAnalysisEngine
    교체: RealMediaPipeEngine  ← 이 한 줄만 바꾸면 실제 AI 분석으로 전환
    """

    def __init__(
        self,
        engine_factory: Callable[[], IAnalysisEngine],
        report_service: SessionReportService,
    ) -> None:
        self._engine_factory  = engine_factory
        self._report_service  = report_service
        self._is_running:     bool                            = False
        self._start_time:     Optional[float]                 = None
        self._webcam_service: Optional[WebcamAnalysisService] = None
        self._data:           Optional[SessionData]           = None
        self._future:         Optional[asyncio.Future]        = None

    async def start(self) -> dict:
        """세션 초기화 → 웹캠 루프를 executor 스레드로 기동."""
        if self._is_running:
            raise RuntimeError("이미 실행 중인 세션이 있습니다.")

        self._data           = SessionData()
        engine               = self._engine_factory()
        self._webcam_service = WebcamAnalysisService(engine, self._data)
        self._is_running     = True
        self._start_time     = time.time()

        loop         = asyncio.get_running_loop()
        self._future = loop.run_in_executor(None, self._webcam_service.run)

        return {"status": "started", "message": "웹캠 분석이 시작되었습니다."}

    async def stop(self) -> dict:
        """종료 신호 전송 → 스레드 완전 종료 대기 → 정산 및 전송."""
        if not self._is_running:
            raise RuntimeError("실행 중인 세션이 없습니다.")

        self._webcam_service.request_stop()
        end_time = time.time()

        if self._future:
            await self._future       # 블로킹 스레드가 완전히 끝날 때까지 대기

        self._is_running = False

        result      = self._report_service.calculate(self._data, self._start_time, end_time)
        sync_status = await self._report_service.send(result)

        return {
            "status":      "stopped",
            "backendSync": sync_status,
            "result":      result.model_dump(),
        }


# ==============================================================
# ⑨ FastAPI 앱 + CORS 미들웨어 + 의존성 조립
# ==============================================================
app = FastAPI(
    title       = "Critical Flow AI",
    description = "학습 집중도 실시간 분석 API",
    version     = "1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── 의존성 조립 (Dependency Wiring) ────────────────────────────
#   engine_factory 를 RealMediaPipeEngine 으로 교체하면
#   이 한 줄 외에는 코드 변경 없이 실제 AI 분석으로 전환 가능.
# ──────────────────────────────────────────────────────────────
_report_service = SessionReportService(BACKEND_URL, SESSION_ID, USER_ID)
_orchestrator   = SessionOrchestrator(
    engine_factory = SimulatedAnalysisEngine,   # ← 교체 포인트
    report_service = _report_service,
)


# ==============================================================
# ⑩ API 엔드포인트
# ==============================================================
@app.post("/start", summary="웹캠 집중도 분석 시작")
async def start_session():
    """이전 상태를 초기화하고 웹캠 분석을 백그라운드 스레드로 실행."""
    try:
        return await _orchestrator.start()
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/stop", summary="분석 종료 및 백엔드 전송")
async def stop_session():
    """루프를 안전하게 종료하고 집계 데이터를 Spring Boot 서버로 전송."""
    try:
        return await _orchestrator.stop()
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


# ==============================================================
# ⑪ 실행 진입점
#    reload=False — run_in_executor 스레드와 핫 리로드 충돌 방지
# ==============================================================
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
