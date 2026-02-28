import sys
from PySide6.QtWidgets import QApplication

from ui_main import YtDownloaderUI
from yt_worker import DownloadWorker


class AppController:
    """
    UI 클래스와 비즈니스 로직(yt_core)을 중개하는 컨트롤러 객체.
    뷰의 시그널(Signal)과 로직의 슬롯(Slot)을 이어주는 역할을 합니다.
    """

    def __init__(self):
        self.ui = YtDownloaderUI()
        self.worker = None

        # UI 위젯의 이벤트(Signal) 연결
        self.ui.start_btn.clicked.connect(self.on_start_download)
        self.ui.window_closed.connect(self.on_window_closed)

    def show(self):
        """메인 윈도우를 화면에 띄웁니다."""
        self.ui.show()

    def on_start_download(self):
        """다운로드 시작 버튼 클릭 시 발생할 비즈니스 로직 처리"""
        # 1. UI에서 데이터 수집
        urls = self.ui.get_url_list()
        if not urls:
            self.ui.append_log("[경고] 다운로드할 URL을 먼저 입력해주세요.")
            return

        download_option_type = self.ui.get_current_download_option_type()
        save_dir = self.ui.get_save_dir()
        time_start, time_end = None, None

        # 2. 탭 3 (구간 다운로드)일 때 시작, 종료 시간 수집
        if download_option_type == 2:
            time_start, time_end = self.ui.get_time_inputs()

        # 3. 로직 실행 전 View 상태 변경
        self.ui.set_downloading_state(True)
        self.ui.clear_log()
        self.ui.append_log("다운로드 스레드 시작 준비 중...")

        # 4. 백그라운드 Worker 스레드(로직) 생성 및 실행
        self.worker = DownloadWorker(
            urls, download_option_type, save_dir, time_start, time_end)

        # Worker의 시그널을 View의 렌더링 메서드에 연결
        self.worker.log_signal.connect(self.ui.append_log)
        self.worker.finished_signal.connect(self.on_download_finished)

        self.worker.start()

    def on_download_finished(self):
        """Worker 스레드가 완료되었을 때 호출되는 콜백"""
        self.ui.set_downloading_state(False)
        self.ui.append_log("--- 작업 스레드가 안전하게 종료되었습니다 ---")

    def on_window_closed(self):
        """윈도우 창이 닫힐 때 자원을 정리하기 위한 콜백"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()  # 스레드가 완전히 종료될 때까지 대기


def main():
    app = QApplication(sys.argv)
    controller = AppController()
    controller.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
