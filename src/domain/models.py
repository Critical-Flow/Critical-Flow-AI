from pydantic import BaseModel


class SessionResult(BaseModel):
    """백엔드 전송용 최종 학습 세션 통계 스키마 (Spring Boot DTO에 대응)."""
    userId:            int
    totalStudySeconds: int
    goodFocusSeconds:  int
    drowsySeconds:     int
    absentSeconds:     int
    drowsyCount:       int
    absentCount:       int
