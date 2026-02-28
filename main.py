import sys
from PySide6.QtWidgets import QApplication

# 분리된 모듈 불러오기
from ui_main import YtDownloaderUI
from yt_core import DownloadWorker, is_valid_time_format

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

        current_tab = self.ui.get_current_tab_index()
        save_dir = self.ui.get_save_dir()
        time_start, time_end = None, None

        # 2. 탭 3 (구간 다운로드)일 때 데이터 유효성 검증
        if current_tab == 2:
            time_start, time_end = self.ui.get_time_inputs()
            
            if time_start and not is_valid_time_format(time_start):
                self.ui.append_log("[오류] 시작 시간 형식이 올바르지 않습니다.")
                return
            if time_end and not is_valid_time_format(time_end):
                self.ui.append_log("[오류] 종료 시간 형식이 올바르지 않습니다.")
                return

        # 3. 로직 실행 전 View 상태 변경
        self.ui.set_downloading_state(True)
        self.ui.clear_log()
        self.ui.append_log("다운로드 스레드 시작 준비 중...")

        # 4. 백그라운드 Worker 스레드(로직) 생성 및 실행
        self.worker = DownloadWorker(urls, current_tab, save_dir, time_start, time_end)
        
        # Worker의 시그널을 View의 렌더링 메서드에 연결
        self.worker.log_signal.connect(self.ui.append_log)
        self.worker.finished_signal.connect(self.on_download_finished)
        
        self.worker.start()

    def on_download_finished(self):
        """Worker 스레드가 완료되었을 때 호출되는 콜백"""
        self.ui.set_downloading_state(False)
        self.ui.append_log("--- 작업 스레드가 안전하게 종료되었습니다 ---")


def main():
    app = QApplication(sys.argv)
    controller = AppController()
    controller.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

