# src/services/drowsiness_manager.py

import time
from collections import deque


class DrowsinessManager:
    """
    연속 눈 감김과 PERCLOS를 이용해 졸음 상태를 판단하는 클래스.

    졸음 진입:
    - EAR < threshold 상태가 closed_seconds 이상 지속
    - 또는 실행 후 PERCLOS window 이후,
      PERCLOS >= threshold 이고 최근 회복 상태가 아닐 때

    졸음 복귀:
    - 최근 recovery_window_seconds 동안 눈 감김 비율이 recovery_closed_ratio 이하
    - 그리고 현재 눈을 뜨고 있음

    자리비움:
    - 얼굴 미검출 상태가 reset_seconds 이상 지속되면 기록 초기화
    """

    def __init__(
        self,
        ear_threshold: float,
        closed_seconds: float,
        perclos_window_seconds: float,
        perclos_threshold: float,
        recovery_window_seconds: float,
        recovery_closed_ratio: float,
        recovery_cooldown_seconds: float,
    ):
        self.ear_threshold = ear_threshold
        self.closed_seconds = closed_seconds
        self.perclos_window_seconds = perclos_window_seconds
        self.perclos_threshold = perclos_threshold
        self.recovery_window_seconds = recovery_window_seconds
        self.recovery_closed_ratio = recovery_closed_ratio
        self.recovery_cooldown_seconds = recovery_cooldown_seconds
        self.last_recovered_time = None

        self.start_time = time.monotonic()
        self.closed_start_time = None
        self.face_lost_start_time = None

        self.history = deque()

        self.is_drowsy = False
        self.closed_duration = 0.0
        self.perclos = 0.0

        self.last_info = self._make_info(
            reason="NORMAL",
            ear=None,
            closed=False,
            elapsed=0.0,
            recovery_closed_ratio=0.0,
        )

    def reset(self):
        """
        자리비움 상태일 때 졸음 기록 초기화.
        """
        self.start_time = time.monotonic()
        self.closed_start_time = None
        self.face_lost_start_time = None
        self.history.clear()

        self.is_drowsy = False
        self.closed_duration = 0.0
        self.perclos = 0.0

        self.last_info = self._make_info(
            reason="RESET",
            ear=None,
            closed=False,
            elapsed=0.0,
            recovery_closed_ratio=0.0,
        )

    def keep_recent_history_only(self, now: float):
        """
        집중 복귀 시점에 오래된 PERCLOS 기록만 제거하고,
        최근 recovery window 기록은 유지한다.
        """
        while self.history and now - self.history[0][0] > self.recovery_window_seconds:
            self.history.popleft()

        if self.history:
            closed_count = sum(1 for _, closed in self.history if closed)
            self.perclos = closed_count / len(self.history)
        else:
            self.perclos = 0.0

        self.closed_start_time = None
        self.closed_duration = 0.0

    def update_face_lost(self, reset_seconds: float) -> dict:
        """
        얼굴이 안 잡힐 때 호출.

        얼굴 미검출은 눈 감음이 아니므로 PERCLOS에 closed=True로 기록하지 않는다.
        reset_seconds 이상 얼굴이 안 잡히면 자리비움으로 보고 기록을 초기화한다.
        """
        now = time.monotonic()

        if self.face_lost_start_time is None:
            self.face_lost_start_time = now

        lost_duration = now - self.face_lost_start_time

        if lost_duration >= reset_seconds:
            self.reset()
            self.last_info = self._make_info(
                reason="FACE_LOST_RESET",
                ear=None,
                closed=False,
                elapsed=0.0,
                recovery_closed_ratio=0.0,
            )
            self.last_info["face_lost_duration"] = lost_duration
            return self.last_info

        info = dict(self.last_info)
        info["reason"] = "FACE_LOST_HOLD"
        info["face_lost_duration"] = lost_duration
        return info

    def update(self, ear: float) -> dict:
        now = time.monotonic()
        elapsed = now - self.start_time

        self.face_lost_start_time = None

        is_closed = ear < self.ear_threshold

        if is_closed:
            if self.closed_start_time is None:
                self.closed_start_time = now
            self.closed_duration = now - self.closed_start_time
        else:
            self.closed_start_time = None
            self.closed_duration = 0.0

        self.history.append((now, is_closed))

        while self.history and now - self.history[0][0] > self.perclos_window_seconds:
            self.history.popleft()

        if self.history:
            closed_count = sum(1 for _, closed in self.history if closed)
            self.perclos = closed_count / len(self.history)
        else:
            self.perclos = 0.0

        recovery_entries = [
            closed
            for timestamp, closed in self.history
            if now - timestamp <= self.recovery_window_seconds
        ]

        if recovery_entries:
            recovery_closed_ratio = sum(recovery_entries) / len(recovery_entries)
        else:
            recovery_closed_ratio = 0.0

        recovery_window_ready = elapsed >= self.recovery_window_seconds

        continuous_drowsy = self.closed_duration >= self.closed_seconds

        perclos_window_ready = elapsed >= self.perclos_window_seconds
        perclos_drowsy = (
            perclos_window_ready
            and self.perclos >= self.perclos_threshold
        )

        recovered = (
            recovery_window_ready
            and not is_closed
            and recovery_closed_ratio <= self.recovery_closed_ratio
        )

        in_recovery_cooldown = (
            self.last_recovered_time is not None
            and now - self.last_recovered_time < self.recovery_cooldown_seconds
        )

        if self.is_drowsy:
            if recovered:
                self.is_drowsy = False
                self.last_recovered_time = now
                self.keep_recent_history_only(now)
            else:
                self.is_drowsy = True
        else:
            if continuous_drowsy:
                self.is_drowsy = True
            elif perclos_drowsy and not recovered and not in_recovery_cooldown:
                self.is_drowsy = True
            else:
                self.is_drowsy = False

        if self.is_drowsy:
            if perclos_drowsy:
                reason = "PERCLOS"
            elif continuous_drowsy:
                reason = "CLOSED_EYES"
            else:
                reason = "DROWSY_HOLD"
        else:
            if recovered:
                reason = "RECOVERED"
            else:
                reason = "NORMAL"

        self.last_info = self._make_info(
            reason=reason,
            ear=ear,
            closed=is_closed,
            elapsed=elapsed,
            recovery_closed_ratio=recovery_closed_ratio,
        )

        return self.last_info

    def _make_info(
        self,
        reason: str,
        ear,
        closed: bool,
        elapsed: float,
        recovery_closed_ratio: float,
    ) -> dict:
        return {
            "is_drowsy": self.is_drowsy,
            "reason": reason,
            "ear": ear,
            "closed": closed,
            "closed_duration": self.closed_duration,
            "perclos": self.perclos,
            "elapsed": elapsed,
            "recovery_closed_ratio": recovery_closed_ratio,
        }