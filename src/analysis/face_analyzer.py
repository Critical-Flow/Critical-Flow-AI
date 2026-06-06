# src/analysis/face_analyzer.py

import math

"""
이탈 및 눈 상태 등 수학적 분석 로직 (FaceAnalyzer 클래스)
"""


class FaceAnalyzer:
    """
    Handles mathematical analysis of face landmarks.
    """

    def __init__(self, ear_threshold, head_pose_threshold=None):
        self.ear_threshold = ear_threshold
        self.head_pose_threshold = head_pose_threshold

    def calculate_ear(self, landmarks, eye_indices):
        """
        Eye Aspect Ratio (EAR) 계산.

        현재 eye_indices는 16개짜리 MediaPipe 눈 인덱스를 사용한다.
        - 가로: eye_indices[0] 과 eye_indices[8]
        - 세로: eye_indices[12] 와 eye_indices[4]
        """
        try:
            p1 = landmarks[eye_indices[0]]
            p2 = landmarks[eye_indices[8]]
            p3 = landmarks[eye_indices[12]]
            p4 = landmarks[eye_indices[4]]

            def dist(a, b):
                return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)

            width = dist(p1, p2)
            height = dist(p3, p4)

            if width == 0:
                return 1.0

            return height / width

        except Exception:
            return 1.0

    def get_avg_ear(self, landmarks, left_eye_indices, right_eye_indices):
        """
        양쪽 눈의 평균 EAR 값을 반환한다.
        얼굴이 없으면 None 반환.
        """
        if not landmarks:
            return None

        left_ear = self.calculate_ear(landmarks, left_eye_indices)
        right_ear = self.calculate_ear(landmarks, right_eye_indices)

        return (left_ear + right_ear) / 2.0

    def get_frame_violation(self, landmarks, left_eye_indices, right_eye_indices):
        """
        현재 프레임에서 집중 위반 상태를 판단한다.

        반환값:
            - "이탈": 얼굴 미검출
            - "눈 감음": EAR 기준 눈 감김
            - None: 정상
        """
        if not landmarks:
            return "이탈"

        avg_ear = self.get_avg_ear(landmarks, left_eye_indices, right_eye_indices)

        if avg_ear is None:
            return "이탈"

        if avg_ear < self.ear_threshold:
            return "눈 감음"

        return None
