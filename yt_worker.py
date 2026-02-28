import os
import subprocess
from PySide6.QtCore import QThread, Signal
from yt_core import build_yt_dlp_command, is_valid_times


class DownloadWorker(QThread):
    """
    다운로드 작업을 비동기로 처리하는 백그라운드 스레드 클래스입니다.
    GUI가 멈추지 않도록 yt-dlp 명령어를 실행하고 로그를 Signal로 전달합니다.
    """
    log_signal = Signal(str)
    finished_signal = Signal()
    yt_dlp_path = "yt-dlp"

    def __init__(self, urls: list[str], download_option_type: int, save_dir: str, time_start: str | None = None, time_end: str | None = None) -> None:
        super().__init__()
        self.urls = urls
        self.download_option_type = download_option_type
        self.save_dir = save_dir
        self.time_start = time_start
        self.time_end = time_end
        self.is_running = True

    def run(self) -> None:
        if (self.download_option_type == 2):
            valid, error_message = is_valid_times(
                self.time_start, self.time_end)
            if not valid:
                self.log_signal.emit(f"[오류] {error_message}")
                self.finished_signal.emit()
                return

        for url in self.urls:
            if not self.is_running:
                break

            url = url.strip()
            if not url:
                continue

            # yt_core의 비즈니스 로직을 호출해 yt-dlp 명령어를 생성
            cmd = build_yt_dlp_command(
                yt_dlp_path=self.yt_dlp_path,
                url=url,
                save_dir=self.save_dir,
                download_option_type=self.download_option_type,
                time_start=self.time_start,
                time_end=self.time_end
            )

            cmd_str = " ".join(cmd)
            self.log_signal.emit(f"-> 실행 명령어: {cmd_str}")

            env = os.environ.copy()
            env["PYTHONUTF8"] = "1"

            # 프로세스 실행 및 실시간 출력 캡처
            process = subprocess.Popen(
                cmd_str, shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',  # 명시적으로 utf-8 지정
                errors='replace',  # 읽을 수 없는 문자는 대체 문자로 바꿈
                env=env
            )

            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    self.log_signal.emit(line.strip())

        if self.is_running:
            self.log_signal.emit("=== 모든 다운로드 작업이 완료되었습니다 ===")

        self.finished_signal.emit()

    def stop(self) -> None:
        """작업을 안전하게 중단하기 위한 플래그 스위치"""
        self.is_running = False
