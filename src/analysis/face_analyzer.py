import math

"""
EAR 및 고개 숙임 등 수학적 분석 로직 (FaceAnalyzer 클래스)
"""

class FaceAnalyzer:
    """
    Handles mathematical analysis of face landmarks.
    """
    def __init__(self, ear_threshold, head_pose_threshold):
        self.ear_threshold = ear_threshold
        self.head_pose_threshold = head_pose_threshold

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

    def check_head_pose(self, landmarks):
        """
        Calculates if the head is tilted down.
        코 끝(1번)과 양 눈 사이(8번)의 Y축 거리 차이를 계산합니다.
        고개를 숙이면 코 끝이 눈 위치보다 상대적으로 더 아래로 내려가므로 이 값이 커집니다.
        """
        nose_tip = landmarks[1]
        between_eyes = landmarks[8]
        # nose_tip.y가 between_eyes.y보다 클수록(아래에 있을수록) 양수 값이 커짐
        return nose_tip.y - between_eyes.y

    def get_frame_violation(self, landmarks, left_eye_indices, right_eye_indices):
        """
        Determines if there is a violation in the current frame based on landmarks.
        """
        if not landmarks:
            return "자리 비움"

        left_ear = self.calculate_ear(landmarks, left_eye_indices)
        right_ear = self.calculate_ear(landmarks, right_eye_indices)
        avg_ear = (left_ear + right_ear) / 2.0
        
        head_diff = self.check_head_pose(landmarks)
        
        if avg_ear < self.ear_threshold:
            return "눈 감음"
        elif head_diff > self.head_pose_threshold:
            return "핸드폰/숙임"
        
        return None
