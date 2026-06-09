import threading
import time
from datetime import datetime

import requests

"""
집중 상태 전환 이벤트를 백엔드 /focus-events 엔드포인트에 POST 전송하는 클라이언트.

[SRP] 네트워크 I/O 만 담당 — 상태 판단 로직 없음.
[Non-blocking] 분석 루프를 막지 않도록 daemon 스레드에서 전송.

[Spring API 스펙]
  POST /api/v1/sessions/{sessionId}/focus-events
  Body: { "eventType": "DROWSY"|"ABSENT", "detectedAt": "ISO-8601", "durationSec": int }

[이벤트 매핑]
  StateManager 가 전송하는 START/END 쌍을 Spring 의 단일 이벤트로 변환:
    DROWSINESS_START → 시작 시각 기록 (전송 안 함)
    DROWSINESS_END   → DROWSY 이벤트 전송 (시작~종료 durationSec 포함)
    AWAY_START       → 시작 시각 기록 (전송 안 함)
    AWAY_END         → ABSENT 이벤트 전송 (시작~종료 durationSec 포함)
"""


class FocusEventClient:
    """
    상태 전환(State Transition) 이벤트를 백엔드 서버로 전송한다.

    START 이벤트 수신 시 → 시작 시각만 기록
    END   이벤트 수신 시 → durationSec 계산 후 Spring API 에 POST
    """

    _TIMEOUT: float = 3.0

    # Python StateManager 이벤트 → (Spring EventType, 역할)
    _EVENT_MAP: dict = {
        "DROWSINESS_START": ("DROWSY",  "start"),
        "DROWSINESS_END":   ("DROWSY",  "end"),
        "AWAY_START":       ("ABSENT",  "start"),
        "AWAY_END":         ("ABSENT",  "end"),
    }

    def __init__(self, url: str, session_id: int) -> None:
        self._url        = url
        self._session_id = session_id
        # spring_event_type → 시작 타임스탬프
        self._start_times: dict = {}

    # ── Public ────────────────────────────────────────────────

    def post_event(self, event_type: str) -> None:
        """
        이벤트를 daemon 스레드에서 비동기로 처리한다.

        START 이벤트: 시작 시각 기록
        END   이벤트: duration 계산 후 Spring API 에 POST
        """
        threading.Thread(
            target=self._handle,
            args=(event_type,),
            daemon=True,
        ).start()

    # ── Private ───────────────────────────────────────────────

    def _handle(self, event_type: str) -> None:
        mapping = self._EVENT_MAP.get(event_type)
        if not mapping:
            return  # 알 수 없는 이벤트 무시

        spring_type, role = mapping

        if role == "start":
            self._start_times[spring_type] = time.time()
            print(f"[EVENT] {event_type} → {spring_type} 시작 시각 기록")
            return

        # role == "end" → Spring API POST
        start_ts = self._start_times.pop(spring_type, None)
        now      = time.time()
        duration = int(now - start_ts) if start_ts is not None else 0
        detected = datetime.fromtimestamp(
            start_ts if start_ts is not None else now
        ).strftime("%Y-%m-%dT%H:%M:%S")

        payload = {
            "eventType":   spring_type,
            "detectedAt":  detected,
            "durationSec": duration,
        }

        self._send(event_type, spring_type, payload, duration)

    def _send(self, event_type: str, spring_type: str, payload: dict, duration: int) -> None:
        """실제 HTTP POST 전송. 모든 예외를 처리하여 프로그램이 중단되지 않도록 한다."""
        try:
            url      = self._url.format(sessionId=self._session_id)
            response = requests.post(url, json=payload, timeout=self._TIMEOUT)
            response.raise_for_status()
            print(
                f"[EVENT] {event_type} → {spring_type} 전송 성공"
                f" ({response.status_code}), {duration}초"
            )

        except requests.exceptions.ConnectionError:
            print(f"[EVENT][ERROR] 서버 연결 실패 — {event_type} 전송 불가")
        except requests.exceptions.Timeout:
            print(f"[EVENT][ERROR] 요청 타임아웃 ({self._TIMEOUT}s) — {event_type}")
        except requests.exceptions.HTTPError as e:
            print(f"[EVENT][ERROR] 서버 오류 {e.response.status_code} — {event_type}")
        except Exception as e:
            print(f"[EVENT][ERROR] 예상치 못한 오류 — {event_type}: {e}")
