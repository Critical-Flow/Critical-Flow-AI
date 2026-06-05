from src.domain.models import SessionResult
from src.domain.session_data import SessionData
from src.repository.backend_client import BackendClient


class SessionReportService:
    """
    학습 세션의 최종 통계를 계산하고 Repository 에 전송을 위임한다.

    [SRP] 비즈니스 계산 로직 + 전송 위임만 담당. 네트워크 I/O 는 BackendClient 에 위임.
    calculate() 와 send() 를 분리하여 테스트 용이성 확보.
    """

    def __init__(self, backend_client: BackendClient) -> None:
        self._backend_client = backend_client

    def calculate(
        self,
        user_id:    int,
        data:       SessionData,
        start_time: float,
        end_time:   float,
    ) -> SessionResult:
        """
        [Data Integrity — 보정 로직]
        totalStudySeconds = 종료 시각 - 시작 시각  (타임스탬프 기준)
        goodFocusSeconds  = total - (drowsy + absent)  ← 역산으로 tick 오차 흡수

        drowsy + absent > total 인 경우:
          → 비율에 따라 비례 스케일 다운 후 역산 적용
        """
        total  = int(end_time - start_time)
        drowsy = data.drowsy_seconds
        absent = data.absent_seconds

        combined = drowsy + absent
        if combined > total:
            scale  = total / combined
            drowsy = int(drowsy * scale)
            absent = total - drowsy

        good = total - (drowsy + absent)

        return SessionResult(
            userId            = user_id,
            totalStudySeconds = total,
            goodFocusSeconds  = good,
            drowsySeconds     = drowsy,
            absentSeconds     = absent,
            drowsyCount       = data.drowsy_count,
            absentCount       = data.absent_count,
        )

    async def send(self, result: SessionResult, session_id: int) -> str:
        """계산된 결과를 Repository 계층(BackendClient)에 전달."""
        return await self._backend_client.post_session_result(result, session_id=session_id)
