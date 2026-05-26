from abc import ABC, abstractmethod

import numpy as np

from src.domain.enums import FocusState


class IAnalysisEngine(ABC):
    """
    프레임 1장을 받아 집중 상태(FocusState)를 반환하는 분석 엔진 인터페이스.

    [OCP] 새 엔진 구현체를 추가해도 기존 코드 수정 불필요.
    [DIP] 상위 레이어(WebcamAnalysisService)가 구체 클래스가 아닌 이 추상에 의존.
    [ISP] 클라이언트가 사용하지 않는 메서드를 강제하지 않도록 3개로 최소화.
    """

    @abstractmethod
    def analyze(self, frame: np.ndarray) -> FocusState:
        """BGR 프레임 1장을 분석하여 집중 상태를 반환."""
        ...

    @abstractmethod
    def get_state_info(self) -> dict:
        """
        UI 렌더링용 현재 상태 정보를 반환.

        반환 형식:
          {
            "status":          str,   # "좋음" | "눈 감음" | "이탈"
            "violation":       str | None,
            "elapsed":         float,
            "is_timer_active": bool,
          }
        """
        ...

    @abstractmethod
    def release(self) -> None:
        """보유 중인 모델 · 파일 핸들 등 리소스를 해제."""
        ...
