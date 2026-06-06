import threading
import time

import requests

"""
졸음 / 자리 이탈 이벤트를 ESP32 HTTP 서버로 POST 전송하는 클라이언트.

[SRP] 네트워크 I/O 만 담당 — 상태 판단 로직 없음.
[Non-blocking] 웹캠 분석 루프를 막지 않도록 daemon 스레드에서 전송.

── ESP32 Arduino 수신 예시 ────────────────────────────────────────────
  #include <WiFi.h>
  #include <WebServer.h>
  #include <ArduinoJson.h>

  WebServer server(80);

  void handleAlert() {
    StaticJsonDocument<128> doc;
    deserializeJson(doc, server.arg("plain"));
    String eventType = doc["eventType"];

    if (eventType == "DROWSINESS_START" || eventType == "AWAY_START") {
      digitalWrite(LED_PIN, HIGH);  // LED / 부저 ON
    } else {
      digitalWrite(LED_PIN, LOW);   // LED / 부저 OFF
    }
    server.send(200, "application/json", "{\"ok\":true}");
  }

  void setup() {
    WiFi.begin(SSID, PASSWORD);
    server.on("/alert", HTTP_POST, handleAlert);
    server.begin();
  }

  void loop() { server.handleClient(); }
───────────────────────────────────────────────────────────────────────
"""


class Esp32Client:
    """
    상태 전환(State Transition) 이벤트를 ESP32 HTTP 서버로 전송한다.

    전송 이벤트 종류:
        DROWSINESS_START  — 졸음 감지 시작  → LED / 부저 ON
        DROWSINESS_END    — 졸음 상태 해제  → LED / 부저 OFF
        AWAY_START        — 자리 이탈 시작  → LED / 부저 ON
        AWAY_END          — 자리 이탈 복귀  → LED / 부저 OFF
    """

    _TIMEOUT: float = 2.0   # ESP32 응답 타임아웃 (초) — 로컬 네트워크이므로 짧게

    def __init__(self, url: str) -> None:
        """
        Args:
            url: ESP32 HTTP 엔드포인트 (예: "http://192.168.0.50/alert")
        """
        self._url = url

    # ── Public ────────────────────────────────────────────────

    def post_event(self, event_type: str) -> None:
        """
        이벤트를 daemon 스레드에서 비동기로 전송한다.

        FocusEventClient 와 동일한 인터페이스를 유지하여
        StateManager 가 두 클라이언트를 동일하게 다룰 수 있도록 한다.
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
            "eventType": event_type,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        }
        try:
            response = requests.post(self._url, json=payload, timeout=self._TIMEOUT)
            response.raise_for_status()
            print(f"[ESP32] {event_type} → 전송 성공 ({response.status_code})")

        except requests.exceptions.ConnectionError:
            print(f"[ESP32][ERROR] ESP32 연결 실패 — {event_type} 전송 불가")
        except requests.exceptions.Timeout:
            print(f"[ESP32][ERROR] 요청 타임아웃 ({self._TIMEOUT}s) — {event_type}")
        except requests.exceptions.HTTPError as e:
            print(f"[ESP32][ERROR] ESP32 오류 {e.response.status_code} — {event_type}")
        except Exception as e:
            print(f"[ESP32][ERROR] 예상치 못한 오류 — {event_type}: {e}")
