from enum import Enum


class FocusState(str, Enum):
    """웹캠 분석으로 판별되는 학습자의 집중 상태."""
    GOOD   = "GOOD"    # 집중
    DROWSY = "DROWSY"  # 졸음
    ABSENT = "ABSENT"  # 자리 이탈
