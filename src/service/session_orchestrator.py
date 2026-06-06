from __future__ import annotations

import time
from typing import Callable, Optional

from src.domain.session_data import SessionData
from src.engine.interface import IAnalysisEngine
from src.service.frame_analysis_service import FrameAnalysisService
from src.service.session_report_service import SessionReportService


class SessionOrchestrator:
    """
    /start · /frame · /stop 요청에 대한 세션 생명주기를 조율하는 Facade 서비스.

    [SRP] 비즈니스 로직 없음 — 각 서비스에 위임하는 조율 책임만 담당.
    Spring 의 @Service (조합 서비스 / Facade) 패턴에 대응.

    [engine_factory]
    매 세션마다 새 엔진 인스턴스를 생성하는 callable.
    SimulatedAnalysisEngine → RealMediaPipeEngine 교체 시
    이 클래스를 포함한 어떤 코드도 수정 불필요 (OCP)

    [아키텍처 변경 이력]
    WebcamAnalysisService (로컬 웹캠 루프) → FrameAnalysisService (HTTP 프레임 수신)
    EC2 환경에는 웹캠이 없으므로, 프론트엔드가 캡처한 프레임을 /vision/frame 으로 수신.
    """

    def __init__(
        self,
        engine_factory: Callable[[int], IAnalysisEngine],
        report_service: SessionReportService,
    ) -> None:
        self._engine_factory  = engine_factory
        self._report_service  = report_service
        self._is_running:     bool                           = False
        self._session_id:     Optional[int]                  = None
        self._user_id:        Optional[int]                  = None
        self._start_time:     Optional[float]                = None
        self._frame_service:  Optional[FrameAnalysisService] = None
        self._data:           Optional[SessionData]          = None

    # ── Public ────────────────────────────────────────────────

    async def start(self, session_id: int, user_id: int) -> dict:
        """세션 초기화 — FrameAnalysisService 준비 (웹캠 루프 없음)."""
        if self._is_running:
            raise RuntimeError("이미 실행 중인 세션이 있습니다.")

        self._session_id    = session_id
        self._user_id       = user_id
        self._data          = SessionData()
        engine              = self._engine_factory(user_id)
        self._frame_service = FrameAnalysisService(engine, self._data)
        self._is_running    = True
        self._start_time    = time.time()

        return {
            "status":  "started",
            "userId":  user_id,
            "message": "프레임 분석 준비 완료. /vision/frame 으로 프레임을 전송하세요.",
        }

    def process_frame(self, frame_bytes: bytes) -> dict:
        """프론트엔드가 전송한 프레임 1장을 분석해 집중 상태를 반환."""
        if not self._is_running or self._frame_service is None:
            raise RuntimeError("실행 중인 세션이 없습니다. /vision/start 를 먼저 호출하세요.")
        return self._frame_service.process_frame(frame_bytes)

    async def stop(self) -> dict:
        """분석 종료 → 집계 결과 Spring 서버로 전송."""
        if not self._is_running:
            raise RuntimeError("실행 중인 세션이 없습니다.")

        end_time = time.time()

        if self._frame_service:
            self._frame_service.release()

        self._is_running = False

        result      = self._report_service.calculate(
            user_id    = self._user_id,
            data       = self._data,
            start_time = self._start_time,
            end_time   = end_time,
        )
        sync_status = await self._report_service.send(result, session_id=self._session_id)

        response = {
            "status":      "stopped",
            "backendSync": sync_status,
            "result":      result.model_dump(),
        }

        # ── 디버그 출력 ───────────────────────────────────────
        import json
        print("\n" + "=" * 50)
        print("📊 [SESSION RESULT]")
        print("=" * 50)
        print(json.dumps(response, indent=2, ensure_ascii=False))
        print("=" * 50 + "\n")
        # ──────────────────────────────────────────────────────

        return response
