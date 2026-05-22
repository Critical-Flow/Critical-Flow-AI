import math

"""
이탈 및 위조 등 수학적 분석 로직 (FaceAnalyzer 클래스)
"""

class FaceAnalyzer:
    """
    Handles mathematical analysis of face landmarks.
    """
    def __init__(self, ear_threshold):
        self.ear_threshold = ear_threshold

    def calculate_ear(self, landmarks, eye_indices):
        """
        Calculates Eye Aspect Ratio (EAR).
        """
        try:
            # Horizontal distance
            p1 = landmarks[eye_indices[0]]
            p2 = landmarks[eye_indices[8]]

            # Vertical distance
            p3 = landmarks[eye_indices[12]]
            p4 = landmarks[eye_indices[4]]

            def dist(a, b):
                return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)

            width = dist(p1, p2)
            height = dist(p3, p4)

            return height / width
        except Exception:
            return 1.0

    def get_frame_violation(self, landmarks, left_eye_indices, right_eye_indices):
        """
        Determines if there is a violation in the current frame based on landmarks.
        """
        if not landmarks:
            return "이탈"

        left_ear = self.calculate_ear(landmarks, left_eye_indices)
        right_ear = self.calculate_ear(landmarks, right_eye_indices)
        avg_ear = (left_ear + right_ear) / 2.0

        if avg_ear < self.ear_threshold:
            return "눈 감음"

        return None
