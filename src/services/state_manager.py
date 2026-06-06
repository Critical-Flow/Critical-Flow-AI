# src/services/state_manager.py

import time
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.repository.focus_event_client import FocusEventClient


"""
집중 상태 판단, 타이머, 상태 전환 이벤트 발송 (StateManager 클래스)
"""


class StateManager:
    """
    집중 상태를 관리하고, 상태가 전환되는 순간 FocusEventClient를 통해
    백엔드로 이벤트를 전송한다.

    이벤트 전송 조건:
    - 상태가 실제로 변경되는 시점에 딱 한 번만 전송
    - 초기화 상태("초기화")에서 최초 정상 상태로의 전환은 전송하지 않음
    """

    _TRANSITION_EVENTS: dict[tuple[str, str], list[str]] = {
        ("좋음", "눈 감음"): ["DROWSINESS_START"],
        ("눈 감음", "좋음"): ["DROWSINESS_END"],

        ("좋음", "졸음"): ["DROWSINESS_START"],
        ("졸음", "좋음"): ["DROWSINESS_END"],

        ("좋음", "이탈"): ["AWAY_START"],
        ("이탈", "좋음"): ["AWAY_END"],

        ("눈 감음", "이탈"): ["DROWSINESS_END", "AWAY_START"],
        ("이탈", "눈 감음"): ["AWAY_END", "DROWSINESS_START"],

        ("졸음", "이탈"): ["DROWSINESS_END", "AWAY_START"],
        ("이탈", "졸음"): ["AWAY_END", "DROWSINESS_START"],

        # 같은 졸음 계열 내부 전환은 이벤트 중복 방지
        ("눈 감음", "졸음"): [],
        ("졸음", "눈 감음"): [],
    }

    def __init__(
        self,
        timeout: float,
        event_client: Optional["FocusEventClient"] = None,
    ) -> None:
        self.timeout = timeout
        self._event_client = event_client

        self.confirmed_status = "좋음"
        self.last_logged_status = "초기화"

        self.distraction_start_time = None
        self.current_violation_type = None
        self.elapsed_time = 0.0

    def update(self, frame_violation: Optional[str]) -> str:
        """
        매 프레임의 위반 여부를 받아 확정된 집중 상태를 반환.
        """
        if frame_violation:
            if self.distraction_start_time is None:
                self.distraction_start_time = time.time()
                self.current_violation_type = frame_violation

            elif frame_violation != self.current_violation_type:
                self.current_violation_type = frame_violation

            self.elapsed_time = time.time() - self.distraction_start_time

            if self.elapsed_time >= self.timeout:
                self.confirmed_status = self.current_violation_type
            else:
                self.confirmed_status = "좋음"

        else:
            self.distraction_start_time = None
            self.current_violation_type = None
            self.confirmed_status = "좋음"
            self.elapsed_time = 0.0

        self._on_state_changed()
        return self.confirmed_status

    def get_current_info(self) -> dict:
        return {
            "status": self.confirmed_status,
            "violation": self.current_violation_type,
            "elapsed": self.elapsed_time,
            "is_timer_active": self.distraction_start_time is not None,
        }

    def _on_state_changed(self) -> None:
        """
        상태가 바뀐 경우에만 실행.
        콘솔 출력 + 이벤트 전송.
        """
        if self.confirmed_status == self.last_logged_status:
            return

        prev = self.last_logged_status
        new = self.confirmed_status

        current_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print(f"[{current_time_str}] 상태 변경: {prev} → {new}")

        if self._event_client is not None and prev != "초기화":
            for event_type in self._TRANSITION_EVENTS.get((prev, new), []):
                self._event_client.post_event(event_type)

        self.last_logged_status = new