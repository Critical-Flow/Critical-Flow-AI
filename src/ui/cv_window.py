import cv2

from src.core.config import COLOR_CONCENTRATED, COLOR_DISTRACTED, FONT_FACE


class UIManager:
    """
    OpenCV 창 관리 및 상태 오버레이 렌더링.

    render() 가 받는 state_info 형식 (StateManager.get_current_info() 출력):
      {
        "status":          str,        # "좋음" | "눈 감음" | "이탈"
        "violation":       str | None,
        "elapsed":         float,      # 현재 위반 지속 시간 (초)
        "is_timer_active": bool,
      }
    """

    # 상태 한국어 → 영어 표시 매핑
    _LABEL_MAP = {
        "좋음":    "GOOD",
        "눈 감음": "DROWSY",
        "이탈":    "ABSENT",
    }

    def __init__(self, window_name: str) -> None:
        self.window_name = window_name

    def render(self, image, state_info: dict) -> None:
        """프레임 위에 집중 상태를 오버레이하고 창에 출력."""
        status    = state_info["status"]
        violation = state_info["violation"]
        elapsed   = state_info["elapsed"]

        color        = COLOR_CONCENTRATED if status == "좋음" else COLOR_DISTRACTED
        label        = self._LABEL_MAP.get(status, status)

        # ── 메인 상태 텍스트 (좌상단) ─────────────────────────
        cv2.putText(image, label, (30, 50), FONT_FACE, 1.2, color, 2)

        # ── 상세 정보: 위반 중일 때 경과 시간, 아닐 때 "Stable" ─
        if state_info["is_timer_active"] and violation:
            violation_label = self._LABEL_MAP.get(violation, violation)
            detail = f"{violation_label}  {elapsed:.1f}s"
        else:
            detail = "Stable"

        cv2.putText(image, detail, (30, 90), FONT_FACE, 0.75, color, 2)

        cv2.imshow(self.window_name, image)
        cv2.waitKey(1)   # 창 이벤트 처리에 필수 (키 입력 감지 목적 아님)

    def close(self) -> None:
        """모든 OpenCV 창 닫기."""
        cv2.destroyAllWindows()
