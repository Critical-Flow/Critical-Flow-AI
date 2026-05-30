import threading
import time

import requests

"""
집중 상태 전환 이벤트를 백엔드 /focus-events 엔드포인트에 POST 전송하는 클라이언트.

[SRP] 네트워크 I/O 만 담당 — 상태 판단 로직 없음.
[Non-blocking] 웹캠 분석 루프를 막지 않도록 daemon 스레드에서 전송.
"""


class FocusEventClient:
    """
    상태 전환(State Transition) 이벤트를 백엔드 서버로 전송한다.

    전송 이벤트 종류:
        DROWSINESS_START  — 졸음 감지 시작
        DROWSINESS_END    — 졸음 상태 해제
        AWAY_START        — 자리 이탈 시작
        AWAY_END          — 자리 이탈 복귀
    """

    _TIMEOUT: float = 3.0   # 요청 타임아웃 (초)

    def __init__(self, url: str, user_id: int) -> None:
        self._url     = url
        self._user_id = user_id

    # ── Public ────────────────────────────────────────────────

    def post_event(self, event_type: str) -> None:
        """
        이벤트를 daemon 스레드에서 비동기로 전송한다.

        웹캠 분석 루프 스레드를 블로킹하지 않기 위해
        HTTP 요청은 별도 daemon 스레드에 위임한다.
        """
        threading.Thread(
            target=self._send,
            args=(event_type,),
            daemon=True,
        ).start()

    # ── Private ───────────────────────────────────────────────

    def _send(self, event_type: str) -> None:
        """실제 HTTP POST 전송. 모든 예외를 처리하여 프로그램이 중단되지 않도록 한다."""
        payload = {
            "userId":    self._user_id,
            "eventType": event_type,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        }
        try:
            url = self._url.format(userId=self._user_id)
            response = requests.post(url, json=payload, timeout=self._TIMEOUT)
            response.raise_for_status()
            print(f"[EVENT] {event_type} → 전송 성공 ({response.status_code})")

        except requests.exceptions.ConnectionError:
            print(f"[EVENT][ERROR] 서버 연결 실패 — {event_type} 전송 불가")
        except requests.exceptions.Timeout:
            print(f"[EVENT][ERROR] 요청 타임아웃 ({self._TIMEOUT}s) — {event_type}")
        except requests.exceptions.HTTPError as e:
            print(f"[EVENT][ERROR] 서버 오류 {e.response.status_code} — {event_type}")
        except Exception as e:
            print(f"[EVENT][ERROR] 예상치 못한 오류 — {event_type}: {e}")
