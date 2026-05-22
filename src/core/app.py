import cv2
from src.core import config
from src.detection.face_detector import FaceDetector
from src.analysis.face_analyzer import FaceAnalyzer
from src.services.state_manager import StateManager
from src.ui.cv_window import UIManager

"""
각 컴포넌트를 조립하여 앱 실행 (ConcentrationApp 클래스)
"""

class ConcentrationApp:
    """
    Main Application Controller that orchestrates all components.
    """
    def __init__(self):
        self.detector = FaceDetector()
        self.analyzer = FaceAnalyzer(config.EAR_THRESHOLD)
        self.state_mgr = StateManager(config.DISTRACTION_TIMEOUT, config.LOG_FILE)
        self.ui = UIManager(config.WINDOW_NAME)
        self.cap = None

    def run(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("Error: Could not open webcam.")
            return

        print(f"Starting {config.WINDOW_NAME}. Press 'q' to quit.")

        try:
            while self.cap.isOpened():
                success, image = self.cap.read()
                if not success:
                    break

                # Pre-processing
                image = cv2.flip(image, 1)
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                
                # Detection
                landmarks = self.detector.process(image_rgb)
                
                # Analysis
                violation = self.analyzer.get_frame_violation(
                    landmarks, config.LEFT_EYE, config.RIGHT_EYE
                )
                
                # State Update
                self.state_mgr.update(violation)
                
                # UI Rendering
                self.ui.render(image, self.state_mgr.get_current_info())

                if self.ui.should_exit():
                    break
        finally:
            self._cleanup()

    def _cleanup(self):
        if self.cap:
            self.cap.release()
        self.detector.close()
        self.ui.close()
        print("Application closed.")
