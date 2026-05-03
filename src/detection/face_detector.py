import mediapipe as mp

"""
MediaPipe Face Mesh 초기화 및 처리 (FaceDetector 클래스)
"""

class FaceDetector:
    """
    Handles MediaPipe Face Mesh initialization and processing.
    """
    def __init__(self, max_num_faces=1, refine_landmarks=True, 
                 min_detection_confidence=0.5, min_tracking_confidence=0.5):
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=max_num_faces,
            refine_landmarks=refine_landmarks,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

    def process(self, image_rgb):
        """
        Processes an RGB image and returns the landmarks.
        """
        results = self.face_mesh.process(image_rgb)
        if results.multi_face_landmarks:
            return results.multi_face_landmarks[0].landmark
        return None

    def close(self):
        """
        Closes the MediaPipe resource.
        """
        self.face_mesh.close()
