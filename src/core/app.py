from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.session_router import create_session_router
from src.core.config import BACKEND_URL, FOCUS_EVENTS_URL
from src.engine.mediapipe_engine import RealMediaPipeEngine
from src.repository.backend_client import BackendClient
from src.service.session_orchestrator import SessionOrchestrator
from src.service.session_report_service import SessionReportService


def create_app() -> FastAPI:
    """
    FastAPI 앱 팩토리 함수 — 의존성을 조립하고 라우터를 등록한 뒤 앱을 반환.

    Spring 의 @SpringBootApplication + @Configuration 역할.
    엔진 교체 시 engine_factory 한 줄만 수정하면 됩니다:
      SimulatedAnalysisEngine  →  RealMediaPipeEngine  (OCP)
    """

    # ── ① 의존성 조립 (Dependency Wiring) ────────────────────
    backend_client = BackendClient(url=BACKEND_URL)
    report_service = SessionReportService(backend_client=backend_client)
    orchestrator   = SessionOrchestrator(
        engine_factory = RealMediaPipeEngine,
        report_service = report_service,
    )

    # ── ② FastAPI 앱 생성 ─────────────────────────────────────
    app = FastAPI(
        title       = "Critical Flow AI",
        description = "학습 집중도 실시간 분석 API",
        version     = "1.0.0",
    )

    # ── ③ CORS 미들웨어 등록 ──────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins     = ["*"],
        allow_credentials = True,
        allow_methods     = ["*"],
        allow_headers     = ["*"],
    )

    # ── ④ 라우터 등록 (의존성 주입) ───────────────────────────
    app.include_router(create_session_router(orchestrator))

    return app
