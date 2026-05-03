import time
import os

"""
집중 상태 판단, 타이머, 로그 기록 (StateManager 클래스)
"""

class StateManager:
    """
    Manages concentration state, timers, and logging.
    """
    def __init__(self, timeout, log_file):
        self.timeout = timeout
        self.log_file = log_file
        
        self.confirmed_status = "집중 상태"
        self.last_logged_status = "초기화"
        self.distraction_start_time = None
        self.current_violation_type = None
        self.elapsed_time = 0.0

    def update(self, frame_violation):
        """
        Updates the state based on the current frame's violation.
        """
        if frame_violation:
            if self.distraction_start_time is None:
                self.distraction_start_time = time.time()
                self.current_violation_type = frame_violation
            
            self.elapsed_time = time.time() - self.distraction_start_time
            
            if self.elapsed_time >= self.timeout:
                self.confirmed_status = f"비집중 ({self.current_violation_type})"
            else:
                self.confirmed_status = "집중 상태"
        else:
            self.distraction_start_time = None
            self.current_violation_type = None
            self.confirmed_status = "집중 상태"
            self.elapsed_time = 0.0

        self._log_if_changed()
        return self.confirmed_status

    def _log_if_changed(self):
        if self.confirmed_status != self.last_logged_status:
            current_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            log_message = f"[{current_time_str}] 상태 변경: {self.confirmed_status}"
            print(log_message)
            
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_message + "\n")
            
            self.last_logged_status = self.confirmed_status

    def get_current_info(self):
        return {
            "status": self.confirmed_status,
            "violation": self.current_violation_type,
            "elapsed": self.elapsed_time,
            "is_timer_active": self.distraction_start_time is not None
        }
