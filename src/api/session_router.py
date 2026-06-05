from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.service.session_orchestrator import SessionOrchestrator


class StartRequest(BaseModel):
    sessionId: int
    userId: int


class StopRequest(BaseModel):
    sessionId: int


def create_session_router(orchestrator: SessionOrchestrator) -> APIRouter:
    """
    SessionOrchestrator 를 주입받아 APIRouter 를 생성하는 팩토리 함수.

    Spring 의 @RestController + 생성자 의존성 주입 패턴에 대응.
    라우터가 직접 비즈니스 로직을 갖지 않고 Orchestrator 에 위임 (SRP).

    Spring PythonVisionClient 호출 경로:
        POST /vision/start  body: { sessionId, userId }
        POST /vision/stop   body: { sessionId }
    """
    router = APIRouter(prefix="/vision")

    @router.post("/start", summary="웹캠 집중도 분석 시작")
    async def start_session(body: StartRequest):
        """
        Spring 에서 sessionId, userId 를 body 로 전송.
        예시: POST /vision/start  { "sessionId": 1, "userId": 123 }
        """
        try:
            return await orchestrator.start(session_id=body.sessionId, user_id=body.userId)
        except RuntimeError as e:
            raise HTTPException(status_code=409, detail=str(e))

    @router.post("/stop", summary="분석 종료 및 백엔드 전송")
    async def stop_session(body: StopRequest):
        """루프를 안전하게 종료하고 집계 데이터를 Spring Boot 서버로 전송."""
        try:
            return await orchestrator.stop()
        except RuntimeError as e:
            raise HTTPException(status_code=409, detail=str(e))

    return router
