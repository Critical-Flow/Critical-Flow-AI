import httpx

from src.domain.models import SessionResult


class BackendClient:
    """
    외부 Spring Boot 백엔드와 통신하는 HTTP 클라이언트.

    [SRP] 네트워크 I/O 만 담당 — 비즈니스 로직 없음.
    Spring 의 RestTemplate / WebClient 에 대응하는 Repository 역할.
    """

    def __init__(self, url: str) -> None:
        self._url = url

    async def post_session_result(self, result: SessionResult, session_id: int) -> str:
        """학습 세션 결과를 백엔드에 POST 전송하고 처리 결과를 반환."""
        url = self._url.format(sessionId=session_id)
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    json=result.model_dump(),
                    timeout=10.0,
                )
                response.raise_for_status()
                return "success"

            except httpx.HTTPStatusError as e:
                return f"backend_error ({e.response.status_code})"
            except httpx.RequestError as e:
                return f"connection_error: {e}"
