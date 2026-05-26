from __future__ import annotations

import asyncio
import time
from typing import Callable, Optional

from src.domain.session_data import SessionData
from src.engine.interface import IAnalysisEngine
from src.service.session_report_service import SessionReportService
from src.service.webcam_analysis_service import WebcamAnalysisService


class SessionOrchestrator:
    """
    /start · /stop 요청에 대한 세션 생명주기를 조율하는 Facade 서비스.

    [SRP] 비즈니스 로직 없음 — 각 서비스에 위임하는 조율 책임만 담당.
    Spring 의 @Service (조합 서비스 / Facade) 패턴에 대응.

    [engine_factory]
    매 세션마다 새 엔진 인스턴스를 생성하는 callable.
    SimulatedAnalysisEngine → RealMediaPipeEngine 교체 시
    이 클래스를 포함한 어떤 코드도 수정 불필요
    """

    def __init__(
        self,
        engine_factory: Callable[[], IAnalysisEngine],
        report_service: SessionReportService,
    ) -> None:
        self._engine_factory  = engine_factory
        self._report_service  = report_service
        self._is_running:     bool                            = False
        self._user_id:        Optional[int]                   = None
        self._start_time:     Optional[float]                 = None
        self._webcam_service: Optional[WebcamAnalysisService] = None
        self._data:           Optional[SessionData]           = None
        self._future:         Optional[asyncio.Future]        = None

    async def start(self, user_id: int) -> dict:
        """세션 초기화 → 웹캠 루프를 executor 스레드로 기동."""
        if self._is_running:
            raise RuntimeError("이미 실행 중인 세션이 있습니다.")

        self._user_id        = user_id
        self._data           = SessionData()
        engine               = self._engine_factory()
        self._webcam_service = WebcamAnalysisService(engine, self._data)
        self._is_running     = True
        self._start_time     = time.time()

        loop         = asyncio.get_running_loop()
        self._future = loop.run_in_executor(None, self._webcam_service.run)

        return {"status": "started", "userId": user_id, "message": "웹캠 분석이 시작되었습니다."}

    async def stop(self) -> dict:
        """종료 신호 전송 → 스레드 완전 종료 대기 → 정산 및 전송."""
        if not self._is_running:
            raise RuntimeError("실행 중인 세션이 없습니다.")

        self._webcam_service.request_stop()
        end_time = time.time()

        if self._future:
            await self._future

        self._is_running = False

        result      = self._report_service.calculate(
            user_id    = self._user_id,
            data       = self._data,
            start_time = self._start_time,
            end_time   = end_time,
        )
        sync_status = await self._report_service.send(result)

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
