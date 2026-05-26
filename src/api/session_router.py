from fastapi import APIRouter, HTTPException

from src.service.session_orchestrator import SessionOrchestrator


def create_session_router(orchestrator: SessionOrchestrator) -> APIRouter:
    """
    SessionOrchestrator 를 주입받아 APIRouter 를 생성하는 팩토리 함수.

    Spring 의 @RestController + 생성자 의존성 주입 패턴에 대응.
    라우터가 직접 비즈니스 로직을 갖지 않고 Orchestrator 에 위임 (SRP).
    """
    router = APIRouter()

    @router.post("/start", summary="웹캠 집중도 분석 시작")
    async def start_session(userId: int):
        """
        userId 를 쿼리 파라미터로 받아 웹캠 분석을 시작한다.

        예시: POST /start?userId=123
        """
        try:
            return await orchestrator.start(user_id=userId)
        except RuntimeError as e:
            raise HTTPException(status_code=409, detail=str(e))

    @router.post("/stop", summary="분석 종료 및 백엔드 전송")
    async def stop_session():
        """루프를 안전하게 종료하고 집계 데이터를 Spring Boot 서버로 전송."""
        try:
            return await orchestrator.stop()
        except RuntimeError as e:
            raise HTTPException(status_code=409, detail=str(e))

    return router
