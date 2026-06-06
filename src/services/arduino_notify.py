import time
import serial
import serial.tools.list_ports


DEFAULT_BAUD        = 115200
SERIAL_TIMEOUT      = 2.0
ARDUINO_RESET_DELAY = 2.0


class ArduinoNotifier:
    """
    비집중 상태를 감지하면 solenoid_driver 펌웨어에
    PULSE / BURST 명령을 보내는 클래스.

    dry_run=True 이면 실제 포트 없이 콘솔에만 출력.
    """

    def __init__(
        self,
        port: str = None,
        baudrate: int = DEFAULT_BAUD,
        pulse_ms: int =50,
        burst_count: int = 1,
        dry_run: bool = False,
    ):
        """
        Args:
            port:        시리얼 포트. None → 자동 탐색.
            baudrate:    115200 (펌웨어와 동일하게).
            pulse_ms:    솔레노이드 ON 지속 시간 (ms). 권장: 100~500.
            burst_count: 1 → PULSE, 2 이상 → BURST (두드리기 횟수).
            dry_run:     True → 포트 없이 로그만 출력.
        """
        self.pulse_ms    = pulse_ms
        self.burst_count = burst_count
        self.dry_run     = dry_run
        self._ser        = None
        self._last_state = None

        if dry_run:
            print("[ArduinoNotifier] dry_run 모드")
            return

        target_port = port or self._auto_detect_port()
        if target_port is None:
            print("[ArduinoNotifier] 포트 없음 → dry_run 전환")
            self.dry_run = True
            return

        try:
            self._ser = serial.Serial(target_port, baudrate, timeout=SERIAL_TIMEOUT)
            time.sleep(ARDUINO_RESET_DELAY)
            self._ser.reset_input_buffer()
            while self._ser.in_waiting:
                self._ser.readline()
            print(f"[ArduinoNotifier] 연결: {target_port} @ {baudrate}bps")
            self._ping()
        except serial.SerialException as e:
            print(f"[ArduinoNotifier] 연결 실패: {e} → dry_run 전환")
            self.dry_run = True

    def notify(self, should_alert: bool, force: bool = False) -> None:
        """
        알림 필요 여부에 따라 솔레노이드를 제어.
        force=True이면 같은 알림 상태가 유지되어도 다시 알림을 보냄.
        """
        if should_alert == self._last_state and not force:
            return

        self._last_state = should_alert

        if not should_alert:
            print("[ArduinoNotifier] 🟢 집중 복귀")
            return

        if self.burst_count > 1:
            self._send_burst(self.burst_count, self.pulse_ms)
        else:
            self._send_pulse(self.pulse_ms)

    def ping(self) -> bool:
        return self._ping()

    def close(self) -> None:
        if self._ser and self._ser.is_open:
            self._ser.close()
            print("[ArduinoNotifier] 포트 닫힘")

    # ──────────────────────────────────────────────
    # 내부 명령 전송
    # ──────────────────────────────────────────────

    def _send_pulse(self, ms: int):
        cmd = f"PULSE {ms}"
        if self.dry_run:
            print(f"[ArduinoNotifier][DRY] {cmd}")
            return
        responses = self._send_command(cmd)
        print(f"[ArduinoNotifier] 🔴 PULSE {ms}ms → {responses}")

    def _send_burst(self, count: int, ms: int):
        cmd = f"BURST {count} {ms}"
        if self.dry_run:
            print(f"[ArduinoNotifier][DRY] {cmd}")
            return
        responses = self._send_command(cmd)
        print(f"[ArduinoNotifier] 🔴 BURST {count}x{ms}ms → {responses}")

    def _ping(self) -> bool:
        if self.dry_run:
            return True
        responses = self._send_command("PING")
        ok = any("PONG" in r for r in responses)
        print(f"[ArduinoNotifier] PING → {'PONG ✓' if ok else '응답 없음 ✗'}")
        return ok

    def _send_command(self, cmd: str) -> list[str]:
        try:
            self._ser.write((cmd + "\n").encode())
            self._ser.flush()
        except serial.SerialException as e:
            print(f"[ArduinoNotifier] 전송 오류: {e}")
            return []

        responses = []
        deadline = time.monotonic() + SERIAL_TIMEOUT
        while time.monotonic() < deadline:
            if self._ser.in_waiting:
                line = self._ser.readline().decode(errors="ignore").strip()
                if line:
                    responses.append(line)
                    if line.startswith(("OK DONE", "ERR", "PONG", "STATUS")):
                        break
                    deadline = time.monotonic() + SERIAL_TIMEOUT
            else:
                time.sleep(0.01)
        return responses

    # ──────────────────────────────────────────────
    # 포트 자동 탐색
    # ──────────────────────────────────────────────

    @staticmethod
    def _auto_detect_port() -> str | None:
        KNOWN_VIDS  = {0x2341, 0x1A86, 0x0403}
        KNOWN_DESCS = ["arduino", "ch340", "cp210", "ftdi", "uart", "usb serial"]
        for p in serial.tools.list_ports.comports():
            desc = (p.description or "").lower()
            if p.vid in KNOWN_VIDS or any(k in desc for k in KNOWN_DESCS):
                print(f"[ArduinoNotifier] 자동 감지: {p.device} — {p.description}")
                return p.device
        ports = serial.tools.list_ports.comports()
        if ports:
            return ports[0].device
        return None
