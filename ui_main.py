import sys
import os
import subprocess
import platform
import webbrowser
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QTextEdit, QLineEdit, QPushButton,
                               QTabWidget, QFileDialog, QDialog)
from PySide6.QtGui import QAction
from PySide6.QtCore import Signal

from yt_core import is_valid_time_format, clean_urls


class CleanUrlDialog(QDialog):
    """플레이리스트 ID 등의 URL 파라미터를 일괄 제거해주는 UI 다이얼로그"""

    def __init__(self, urls, parent=None):
        super().__init__(parent)
        self.setWindowTitle("플레이리스트 ID 등 파라미터 제거")
        self.resize(500, 300)

        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()

        # yt_core의 비즈니스 로직(clean_urls)을 호출하여 처리
        cleaned_urls = clean_urls(urls)

        self.text_edit.setPlainText("\n".join(cleaned_urls))
        layout.addWidget(QLabel("파라미터가 제거된 URL 목록:"))
        layout.addWidget(self.text_edit)

        btn_layout = QHBoxLayout()
        apply_btn = QPushButton("내용 적용")
        apply_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("취소 닫기")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def get_cleaned_urls(self):
        return self.text_edit.toPlainText()


def show_clean_url_dialog(parent_ui):
    """
    도구: 파라미터 제거 팝업 띄우기 함수(컨트롤러 역할)
    다이얼로그에서 정리가 완료되면 parent_ui(여기서는 메인 윈도우의 QTextEdit)에 텍스트를 업데이트 한다.
    """
    urls = parent_ui.url_input.toPlainText().split('\n')
    dialog = CleanUrlDialog(urls, parent_ui)
    if dialog.exec() == QDialog.Accepted:
        cleaned_text = dialog.get_cleaned_urls()
        parent_ui.url_input.setPlainText(cleaned_text)
        # 화면의 repaint 유도 (필요한 경우)
        parent_ui.url_input.repaint()


class YtDownloaderUI(QMainWindow):
    """
    GUI 컴포넌트의 구성과 레이아웃 설정만을 담당하는 뷰(View) 클래스
    내부 로직은 포함하지 않으며 시그널 연결은 컨트롤러(main.py)에서 수행합니다.
    """
    window_closed = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("yt-dlp GUI Helper")
        self.resize(750, 700)

        self._init_menu()
        self._init_ui()

    def _init_menu(self):
        """상단 메뉴바 초기화"""
        menubar = self.menuBar()

        # 도구 메뉴
        self.tool_menu = menubar.addMenu("도구")
        self.clean_url_action = QAction("플레이리스트 ID 제거", self)
        self.clean_url_action.triggered.connect(self.open_clean_url_dialog)
        self.tool_menu.addAction(self.clean_url_action)

        # 링크 메뉴
        self.link_menu = menubar.addMenu("링크")
        self.ytdlp_action = QAction("yt-dlp 릴리즈 페이지", self)
        self.ytdlp_action.triggered.connect(lambda: webbrowser.open(
            "https://github.com/yt-dlp/yt-dlp/releases"))
        self.link_menu.addAction(self.ytdlp_action)

        self.ffmpeg_action = QAction("ffmpeg 홈페이지", self)
        self.ffmpeg_action.triggered.connect(
            lambda: webbrowser.open("https://ffmpeg.org/download.html"))
        self.link_menu.addAction(self.ffmpeg_action)

    def _init_ui(self):
        """전체 메인 레이아웃 및 위젯 초기화"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 1. URL 입력창
        main_layout.addWidget(QLabel("1. 다운로드 대상 URL (줄바꿈입력 시 순차 작업):"))
        self.url_input = QTextEdit()
        self.url_input.setFixedHeight(100)
        main_layout.addWidget(self.url_input)

        # 2. 저장 경로 설정
        main_layout.addWidget(QLabel("2. 저장 위치 설정:"))
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setText(os.getcwd())
        self.path_btn = QPushButton("폴더 선택")
        self.path_btn.clicked.connect(self.select_download_path)

        self.open_path_btn = QPushButton("폴더 열기")
        self.open_path_btn.clicked.connect(self.open_download_path)

        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.path_btn)
        path_layout.addWidget(self.open_path_btn)
        main_layout.addLayout(path_layout)

        # 3. 탭 위젯 설정
        main_layout.addWidget(QLabel("\n3. 다운로드 옵션 선택:"))
        self.tabs = QTabWidget()
        self._setup_tabs()
        main_layout.addWidget(self.tabs)

        # 4. 다운로드 실행 버튼
        self.start_btn = QPushButton("선택한 탭의 옵션으로 다운로드 시작")
        self.start_btn.setMinimumHeight(45)
        main_layout.addWidget(self.start_btn)

        # 5. 콘솔/로그 창
        main_layout.addWidget(QLabel("진행 로그 (콘솔 출력):"))
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet(
            "background-color: black; color: white; font-family: Consolas;")
        main_layout.addWidget(self.log_view)

    def closeEvent(self, event):
        """
        메인 윈도우가 닫힐 때 발생하는 이벤트입니다.
        컨트롤러에 이를 알려주어 진행중인 워커가 있다면 정리할 수 있게 합니다.
        """
        self.window_closed.emit()
        super().closeEvent(event)

    def _setup_tabs(self):
        """각 탭의 UI 레이아웃을 구성합니다"""
        # 기능별 탭 위젯 생성
        self.tab_basic = QWidget()
        self.tab_premiere_full = QWidget()
        self.tab_premiere_section = QWidget()
        self.tab_mp3 = QWidget()

        self.tabs.addTab(self.tab_basic, "1. 기본 다운로드")
        self.tabs.addTab(self.tab_premiere_full, "2. 프리미어 프로 (전체)")
        self.tabs.addTab(self.tab_premiere_section, "3. 프리미어 프로 (구간)")
        self.tabs.addTab(self.tab_mp3, "4. MP3 커버 추출")

        # 탭 1: 기본
        layout1 = QVBoxLayout(self.tab_basic)
        layout1.addWidget(QLabel("가장 기본적인 다운로드 기능입니다.\n"
                                 "yt-dlp의 기본 값으로 영상을 다운로드 합니다."))
        layout1.addStretch()

        # 탭 2: 프리미어 (전체)
        layout2 = QVBoxLayout(self.tab_premiere_full)
        layout2.addWidget(QLabel("프리미어 프로 편집 호환성을 위해 다운로드합니다.\n"
                                 "- 영상 코덱: H.264 (avc1)\n"
                                 "- 오디오 코덱: AAC (m4a)\n"
                                 "- 결과물: MP4 컨테이너"))
        layout2.addStretch()

        # 탭 3: 프리미어 (구간)
        layout3 = QVBoxLayout(self.tab_premiere_section)
        layout3.addWidget(QLabel("영상의 특정 구간을 다운로드 합니다. (H.264/AAC MP4)\n"
                                 "시간 형식 예시: [HH:MM:SS], [MM:SS], [SS]\n"
                                 "잘못된 형식을 입력하면 분홍색이 표시됩니다."))

        time_layout = QHBoxLayout()
        self.start_time_input = QLineEdit()
        self.start_time_input.setPlaceholderText("시작 (예: 00:00)")
        self.start_time_input.textChanged.connect(self._validate_time_inputs)

        self.end_time_input = QLineEdit()
        self.end_time_input.setPlaceholderText("종료 (예: 01:30)")
        self.end_time_input.textChanged.connect(self._validate_time_inputs)

        time_layout.addWidget(QLabel("시작:"))
        time_layout.addWidget(self.start_time_input)
        time_layout.addWidget(QLabel("종료:"))
        time_layout.addWidget(self.end_time_input)
        time_layout.addStretch()
        layout3.addLayout(time_layout)
        layout3.addStretch()

        # 탭 4: MP3
        layout4 = QVBoxLayout(self.tab_mp3)
        layout4.addWidget(QLabel("최고 음질의 오디오를 MP3 형식으로 저장합니다.\n"
                                 "영상 썸네일을 MP3 메타데이터 커버로 등록합니다."))
        layout4.addStretch()

    # --- UI 상호작용 관련 기본 동작 ---
    def select_download_path(self):
        """폴더 선택 다이얼로그"""
        directory = QFileDialog.getExistingDirectory(
            self, "저장 폴더 선택", self.path_input.text())
        if directory:
            self.path_input.setText(directory)

    def open_download_path(self):
        """설정된 저장 위치를 엽니다 (Windows: 탐색기, Mac: 파인더)"""
        path = self.path_input.text()
        if not os.path.exists(path):
            self.append_log(f"[경고] 존재하지 않는 경로입니다: {path}")
            return

        try:
            current_os = platform.system()
            if current_os == 'Windows':
                os.startfile(path)
            elif current_os == 'Darwin':  # macOS
                subprocess.Popen(['open', path])
            else:  # Linux (기본 폴더 열기)
                subprocess.Popen(['xdg-open', path])
        except Exception as e:
            self.append_log(f"[오류] 폴더 열기를 실패했습니다: {e}")

    def open_clean_url_dialog(self):
        """도구: 파라미터 제거 팝업 띄우기"""
        show_clean_url_dialog(self)

    def _validate_time_inputs(self):
        """사용자가 텍스트 입력 시 실시간으로 피드백을 주는 시각 효과 담당"""
        def set_style(widget, is_valid):
            if is_valid or not widget.text():
                widget.setStyleSheet("")
            else:
                widget.setStyleSheet("background-color: #ffb3b3;")

        set_style(self.start_time_input, is_valid_time_format(
            self.start_time_input.text().strip()))
        set_style(self.end_time_input, is_valid_time_format(
            self.end_time_input.text().strip()))

    # --- Getter / Setter 영역 ---
    def get_url_list(self):
        return [u for u in self.url_input.toPlainText().split('\n') if u.strip()]

    def get_save_dir(self):
        return self.path_input.text()

    def get_current_download_option_type(self):
        return self.tabs.currentIndex()

    def get_time_inputs(self):
        return self.start_time_input.text().strip(), self.end_time_input.text().strip()

    def append_log(self, text):
        self.log_view.append(text)
        scrollbar = self.log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_log(self):
        self.log_view.clear()

    def set_downloading_state(self, is_downloading):
        if is_downloading:
            self.start_btn.setEnabled(False)
            self.start_btn.setText("다운로드 중...")
        else:
            self.start_btn.setEnabled(True)
            self.start_btn.setText("선택한 탭의 옵션으로 다운로드 시작")
