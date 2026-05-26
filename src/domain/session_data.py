from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.domain.enums import FocusState


@dataclass
class SessionData:
    """
    웹캠 분석 스레드와 API 레이어가 공유하는 세션 누적 데이터.

    [Thread-Safety]
    Python GIL 하에서 int += 1 은 단일 바이트코드 연산이므로
    별도 Lock 없이 안전하게 스레드 간 공유 가능.
    """
    drowsy_seconds: int = 0 # 졸음 상태 누적 시간 (초)
    absent_seconds: int = 0 # 자리 이탈 누적 시간 (초)
    drowsy_count:   int = 0 # 졸음 진입 횟수
    absent_count:   int = 0 # 자리 이탈 진입 횟수
    prev_state:     Optional[FocusState] = field(default=None)

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
