import cv2
from src.core import config

"""
화면 렌더링 및 창 관리 (UIManager 클래스)
"""

class UIManager:
    """
    Handles OpenCV UI rendering and window management.
    """
    def __init__(self, window_name):
        self.window_name = window_name

    def render(self, image, state_info):
        """
        Draws status information on the frame.
        """
        status = state_info["status"]
        violation = state_info["violation"]
        elapsed = state_info["elapsed"]
        
        # Color based on status
        color = config.COLOR_CONCENTRATED if status == "집중 상태" else config.COLOR_DISTRACTED
        
        # Main status
        display_main = "Concentrated" if status == "집중 상태" else "Distracted"
        cv2.putText(image, display_main, (30, 50), config.FONT_FACE, 1, color, 2)
        
        # Detail status
        if state_info["is_timer_active"]:
            detail_text = f"{violation} ({elapsed:.1f}s)"
            # Localization for UI
            detail_text = detail_text.replace("눈 감음", "Eyes Closed")
            detail_text = detail_text.replace("핸드폰/숙임", "Looking Down")
            detail_text = detail_text.replace("자리 비움", "Away")
            cv2.putText(image, detail_text, (30, 90), config.FONT_FACE, 0.7, color, 2)
        else:
            cv2.putText(image, "Stable", (30, 90), config.FONT_FACE, 0.7, color, 2)

        cv2.imshow(self.window_name, image)

    def close(self):
        cv2.destroyAllWindows()

    def should_exit(self):
        return cv2.waitKey(5) & 0xFF == ord('q')
