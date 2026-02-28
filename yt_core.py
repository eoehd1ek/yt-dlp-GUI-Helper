import sys
import os
import re
import subprocess
from PySide6.QtCore import QThread, Signal


def is_valid_time_format(time_str: str) -> bool:
    """
    시간 입력 형식이 올바른지 검증합니다.
    허용 포맷: HH:MM:SS, MM:SS, SS (예: 01:23:45, 12:34, 90)
    """
    if not time_str:
        return False

    pattern = r'^(?:(?:[0-9]{1,2}:)?[0-5]?[0-9]:)?[0-5]?[0-9]$|^[0-9]+$'
    return bool(re.match(pattern, time_str))


def time_str_to_seconds(time_str: str) -> int:
    """
    시/분/초 형식의 문자열을 초(Second) 단위 정수로 변환합니다.
    입력예시: "01:30" -> 90 반환
    """
    if not time_str:
        return 0

    parts = str(time_str).split(':')
    parts.reverse()  # 초, 분, 시 순서로 접근하기 위해 리버스

    try:
        seconds = 0
        for i, part in enumerate(parts):
            seconds += int(part) * (60 ** i)
        return seconds
    except ValueError:
        return -1


def get_premiere_codec_options() -> list[str]:
    """
    프리미어 프로 편집 호환성을 위한 비디오/오디오 코덱 옵션을 반환합니다.
    코덱 제한 없이 최고 화질/음질을 다운로드한 후, MP4(libx264, aac)로 강제 변환합니다.
    """
    return [
        "-f", "bestvideo+bestaudio",
        "--merge-output-format", "mp4",
        "--recode-video", "mp4",
        "--postprocessor-args", '"-c:v libx264 -c:a aac"'
    ]


class DownloadWorker(QThread):
    """
    다운로드 작업을 비동기로 처리하는 백그라운드 스레드 클래스입니다.
    GUI가 멈추지 않도록 yt-dlp 명령어를 실행하고 로그를 Signal로 전달합니다.
    """
    log_signal = Signal(str)
    finished_signal = Signal()
    yt_dlp_path = "yt-dlp"

    def __init__(self, urls: list[str], tab_index: int, save_dir: str, time_start: str | None = None, time_end: str | None = None) -> None:
        super().__init__()
        self.urls = urls
        self.tab_index = tab_index
        self.save_dir = save_dir
        self.time_start = time_start
        self.time_end = time_end
        self.is_running = True

    def run(self) -> None:
        for url in self.urls:
            if not self.is_running:
                break

            url = url.strip()
            if not url:
                continue

            # 공통 옵션: 저장 경로 지정
            cmd = [self.yt_dlp_path, "-P", f'"{self.save_dir}"']

            # --- 탭(기능)별 파라미터 매핑 (새로운 탭/기능 추가 시 여기에 분기 추가) ---
            if self.tab_index == 0:
                # 탭 1: 기본 다운로드 (추가 옵션 없음)
                pass

            elif self.tab_index == 1:
                # 탭 2: 프리미어 프로 전용 (전체)
                cmd.extend(get_premiere_codec_options())

            elif self.tab_index == 2:
                # 탭 3: 프리미어 프로 전용 (구간)
                cmd.extend(get_premiere_codec_options())

                start_sec = time_str_to_seconds(self.time_start)
                end_sec = time_str_to_seconds(self.time_end)

                if (start_sec <= 0 or end_sec <= 0):
                    self.log_signal.emit(
                        "[경고] 시작/종료 시간 입력이 잘못되었습니다. 다운로드를 중지합니다.")
                    continue
                if (end_sec <= start_sec):
                    self.log_signal.emit(
                        "[경고] 종료 시간은 시작 시간보다 커야 합니다. 다운로드를 중지합니다.")
                    continue

                # 구간 다운로드 옵션 조립 (yt-dlp section 지원 시간 양식: *시작초-종료초)
                section_arg = f"*{start_sec}-{end_sec}"
                cmd.extend(
                    ["--download-sections", f'"{section_arg}"', "--force-keyframes-at-cuts"])

            elif self.tab_index == 3:
                # 탭 4: MP3 음원 추출 및 메타데이터 추가
                cmd.extend(["-x", "--audio-format", "mp3", "--audio-quality", "0",
                            "--embed-thumbnail", "--add-metadata"])

            # 마지막으로 다운로드 대상 URL 추가
            cmd.append(f'"{url}"')

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
