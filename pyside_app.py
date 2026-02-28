import sys
import os
import re
import subprocess
import webbrowser
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QTextEdit, QLineEdit, 
                               QPushButton, QTabWidget, QFileDialog, QMenuBar, QMenu, QDialog)
from PySide6.QtGui import QAction
from PySide6.QtCore import QThread, Signal

class Worker(QThread):
    log_signal = Signal(str)
    finished_signal = Signal()

    def __init__(self, urls, tab_index, save_dir, time_start=None, time_end=None):
        super().__init__()
        self.urls = urls
        self.tab_index = tab_index
        self.save_dir = save_dir
        self.time_start = time_start
        self.time_end = time_end
        self.is_running = True

    def run(self):
        # 현재 디렉토리에 yt-dlp.exe가 있으면 사용하고, 아니면 환경 변수의 yt-dlp를 사용
        yt_dlp_path = "yt-dlp.exe" if os.path.exists("yt-dlp.exe") else "yt-dlp"

        for url in self.urls:
            if not self.is_running:
                break
            
            url = url.strip()
            if not url: 
                continue

            # 기본 커맨드 (저장 경로 지정)
            cmd = [yt_dlp_path, "-P", f'"{self.save_dir}"']
            
            if self.tab_index == 0: 
                # 탭 1: 기본 다운로드
                pass
            
            elif self.tab_index == 1: 
                # 탭 2: 프리미어 프로 전용 (전체 길이)
                cmd.extend(["-f", "bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/best[ext=mp4]", "--merge-output-format", "mp4"])
            
            elif self.tab_index == 2: 
                # 탭 3: 프리미어 프로 전용 (구간 길이)
                # yt-dlp의 section 지원 시간 양식: *시작시간-종료시간
                section_arg = f"*{self.time_start}-{self.time_end}"
                cmd.extend(["-f", "bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/best[ext=mp4]", 
                            "--merge-output-format", "mp4", 
                            "--download-sections", f'"{section_arg}"', 
                            "--force-keyframes-at-cuts"])
            
            elif self.tab_index == 3: 
                # 탭 4: MP3 음원 추출
                # -x (extract audio), 오디오 포맷 mp3, 최고 음질 (0), 썸네일 포함 및 메타데이터 추가
                cmd.extend(["-x", "--audio-format", "mp3", "--audio-quality", "0", 
                            "--embed-thumbnail", "--add-metadata"])
            
            # 마지막으로 URL 추가
            cmd.append(f'"{url}"')
            
            cmd_str = " ".join(cmd)
            self.log_signal.emit(f"-> 실행 명령어: {cmd_str}")
            
            # Windows 인코딩 문제를 해결하기 위해 chcp 65001 사용
            if os.name == 'nt':
                cmd_str = f"chcp 65001 > nul & {cmd_str}"

            # 프로세스 실행 및 실시간 로그 캡처
            process = subprocess.Popen(cmd_str, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                       text=True, encoding='utf-8', errors='replace')
            
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    self.log_signal.emit(line.strip())
            
        if self.is_running:
            self.log_signal.emit("=== 모든 다운로드 작업이 완료되었습니다 ===")
            
        self.finished_signal.emit()

    def stop(self):
        self.is_running = False

class CleanUrlDialog(QDialog):
    def __init__(self, urls, parent=None):
        super().__init__(parent)
        self.setWindowTitle("플레이리스트 ID 등 파라미터 제거")
        self.resize(500, 300)
        
        layout = QVBoxLayout(self)
        
        self.text_edit = QTextEdit()
        # '&' 뒤의 파라미터 전부 제거 (유튜브 재생목록 등)
        cleaned_urls = []
        for url in urls:
            url = url.strip()
            if not url: continue
            if "&" in url:
                url = url.split("&")[0]
            cleaned_urls.append(url)
            
        self.text_edit.setPlainText("\n".join(cleaned_urls))
        layout.addWidget(QLabel("파라미터가 제거된 URL 목록:"))
        layout.addWidget(self.text_edit)
        
        btn_layout = QHBoxLayout()
        apply_btn = QPushButton("본창에 적용")
        apply_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("닫기")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def get_cleaned_urls(self):
        return self.text_edit.toPlainText()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("yt-dlp GUI (PySide6 Refactoring)")
        self.resize(750, 700)
        self.worker = None

        self.init_menu()
        self.init_ui()

    def init_menu(self):
        menubar = self.menuBar()
        
        tool_menu = menubar.addMenu("도구")
        clean_url_action = QAction("플레이리스트 ID 제거", self)
        clean_url_action.triggered.connect(self.open_clean_url_dialog)
        tool_menu.addAction(clean_url_action)
        
        link_menu = menubar.addMenu("링크")
        ytdlp_action = QAction("yt-dlp 릴리즈 페이지", self)
        ytdlp_action.triggered.connect(lambda: webbrowser.open("https://github.com/yt-dlp/yt-dlp/releases"))
        link_menu.addAction(ytdlp_action)
        
        ffmpeg_action = QAction("ffmpeg 홈페이지", self)
        ffmpeg_action.triggered.connect(lambda: webbrowser.open("https://ffmpeg.org/download.html"))
        link_menu.addAction(ffmpeg_action)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 1. URL 입력창 
        main_layout.addWidget(QLabel("1. 다운로드 대상 URL (줄바꿈하여 여러 줄 입력 시 순차적으로 작업 수행):"))
        self.url_input = QTextEdit()
        self.url_input.setFixedHeight(100)
        main_layout.addWidget(self.url_input)

        # 2. 저장 경로
        main_layout.addWidget(QLabel("2. 저장 위치 설정:"))
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setText(os.getcwd())
        path_btn = QPushButton("폴더 선택")
        path_btn.clicked.connect(self.select_download_path)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(path_btn)
        main_layout.addLayout(path_layout)

        # 3. 탭 위젯 (기능 분리)
        main_layout.addWidget(QLabel("\n3. 다운로드 옵션 선택:"))
        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()
        self.tab4 = QWidget()

        self.tabs.addTab(self.tab1, "1. 기본 다운로드")
        self.tabs.addTab(self.tab2, "2. 프리미어 프로 (전체)")
        self.tabs.addTab(self.tab3, "3. 프리미어 프로 (구간)")
        self.tabs.addTab(self.tab4, "4. MP3 커버 추출")

        self.setup_tab1()
        self.setup_tab2()
        self.setup_tab3()
        self.setup_tab4()

        main_layout.addWidget(self.tabs)

        # 4. 다운로드 버튼
        self.start_btn = QPushButton("선택한 탭의 옵션으로 다운로드 시작")
        self.start_btn.setMinimumHeight(45)
        self.start_btn.clicked.connect(self.start_download)
        main_layout.addWidget(self.start_btn)

        # 5. 콘솔/로그 창
        main_layout.addWidget(QLabel("진행 로그 (콘솔 출력):"))
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        # 로그 바탕색 검정, 글씨 흰색 처리(가독성)
        self.log_view.setStyleSheet("background-color: black; color: white; font-family: Consolas;")
        main_layout.addWidget(self.log_view)

    def setup_tab1(self):
        layout = QVBoxLayout(self.tab1)
        layout.addWidget(QLabel("가장 기본적인 다운로드 기능입니다.\n별도의 옵션 없이 yt-dlp {URL} 형태로 실행합니다."))
        layout.addStretch()

    def setup_tab2(self):
        layout = QVBoxLayout(self.tab2)
        layout.addWidget(QLabel("프리미어 프로 편집 호환성을 위해 다운로드합니다.\n- 영상 코덱: H.264 (avc1)\n- 오디오 코덱: AAC (mp4a)\n- 결과물은 반드시 MP4 컨테이너로 병합됩니다."))
        layout.addStretch()

    def setup_tab3(self):
        layout = QVBoxLayout(self.tab3)
        layout.addWidget(QLabel("--download-sections 기능을 활용해 특정 구간만 다운로드합니다. (H.264/AAC 코덱 우선)\n\n"
                                "시간 입력 형식: HH:MM:SS, MM:SS, SS (입력 양식이 잘못되면 붉은색으로 표시됩니다)"))
        
        time_layout = QHBoxLayout()
        self.start_time_input = QLineEdit()
        self.start_time_input.setPlaceholderText("시작 시간 (예: 00:00)")
        self.start_time_input.textChanged.connect(self.validate_time_inputs)
        
        self.end_time_input = QLineEdit()
        self.end_time_input.setPlaceholderText("종료 시간 (예: 01:30)")
        self.end_time_input.textChanged.connect(self.validate_time_inputs)

        time_layout.addWidget(QLabel("시작:"))
        time_layout.addWidget(self.start_time_input)
        time_layout.addWidget(QLabel("종료:"))
        time_layout.addWidget(self.end_time_input)
        
        layout.addLayout(time_layout)
        layout.addStretch()

    def setup_tab4(self):
        layout = QVBoxLayout(self.tab4)
        layout.addWidget(QLabel("최고 음질의 오디오만 추출하여 MP3 형식으로 저장합니다.\n영상 썸네일을 다운로드하여 MP3 파일의 커버 이미지(메타데이터)로 추가합니다."))
        layout.addStretch()

    def select_download_path(self):
        directory = QFileDialog.getExistingDirectory(self, "저장 폴더 선택", self.path_input.text())
        if directory:
            self.path_input.setText(directory)

    def open_clean_url_dialog(self):
        # 현재 입력된 URL 데이터를 가져와서 분해
        urls = self.url_input.toPlainText().split('\n')
        dialog = CleanUrlDialog(urls, self)
        if dialog.exec() == QDialog.Accepted:
            # 적용된 값을 본창에 세팅
            self.url_input.setPlainText(dialog.get_cleaned_urls())

    def is_valid_time(self, t_str):
        if not t_str: return False
        # 정규식: 정숫값만 있거나(초 단위), MM:SS 이거나 HH:MM:SS 인 경우만 허용
        # 예: 01:23:45, 12:34, 90, 00:05
        pattern = r'^(?:(?:[0-9]{1,2}:)?[0-5]?[0-9]:)?[0-5]?[0-9]$|^[0-9]+$'
        return bool(re.match(pattern, t_str))

    def validate_time_inputs(self):
        def set_style(widget, is_valid):
            if is_valid or not widget.text():
                # 정상일 경우 기본 배경
                widget.setStyleSheet("")
            else:
                # 오류일 경우 붉은색 배열
                widget.setStyleSheet("background-color: #ffcccc;")

        set_style(self.start_time_input, self.is_valid_time(self.start_time_input.text()))
        set_style(self.end_time_input, self.is_valid_time(self.end_time_input.text()))

    def start_download(self):
        urls = self.url_input.toPlainText().split('\n')
        # 빈칸 제외
        valid_urls = [u for u in urls if u.strip()]
        if not valid_urls:
            self.append_log("[경고] URL을 먼저 입력해주세요.")
            return

        save_dir = self.path_input.text()
        current_tab = self.tabs.currentIndex()

        time_start = None
        time_end = None

        if current_tab == 2: # 구간 길이 탭
            time_start = self.start_time_input.text().strip()
            time_end = self.end_time_input.text().strip()
            
            if not self.is_valid_time(time_start) or not self.is_valid_time(time_end):
                self.append_log("[오류] 입력한 구간 시간이 올바르지 않습니다. HH:MM:SS 나 초단위 형식을 확인하세요.")
                return

        self.start_btn.setEnabled(False)
        self.start_btn.setText("다운로드 중...")
        self.log_view.clear()
        self.append_log("다운로드 시작 준비...")

        # 비동기 처리를 위한 QThread 구동
        self.worker = Worker(valid_urls, current_tab, save_dir, time_start, time_end)
        self.worker.log_signal.connect(self.append_log)
        self.worker.finished_signal.connect(self.on_download_finished)
        self.worker.start()

    def append_log(self, text):
        self.log_view.append(text)
        # 스크롤 최하단으로 자동 이동 방식을 위한 Cursor 조작
        scrollbar = self.log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def on_download_finished(self):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("선택한 탭의 옵션으로 다운로드 시작")
        self.append_log("--- 작업 스레드 종료 ---")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
