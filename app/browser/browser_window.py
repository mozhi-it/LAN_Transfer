from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QProgressBar, QStatusBar, QToolBar, QAction,
    QInputDialog, QLineEdit, QLabel
)
from PyQt5.QtCore import Qt

from .web_engine import WebEngine


# 浏览器主窗口
class BrowserWindow(QMainWindow):
    # 跟踪所有打开的窗口
    _windows = []

    def __init__(self, start_url: str = None):
        super().__init__()
        self.setWindowTitle('LAN Transfer Web客户端连接程序')
        self.resize(1200, 800)
        self._init_ui()
        self._connect_signals()
        BrowserWindow._windows.append(self)
        if start_url:
            self.web_engine.load(start_url)
    # 初始化UI
    def _init_ui(self):
        # 中央控件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 布局
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Web引擎视图
        self.web_engine = WebEngine()
        layout.addWidget(self.web_engine.get_view())

        # 工具栏
        self._create_toolbar()

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(3)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # URL显示标签
        self.url_label = QLabel()
        self.url_label.setMinimumWidth(200)
        self.url_label.setStyleSheet("QLabel { color: #666; }")
        self.status_bar.addPermanentWidget(self.url_label)

    # 创建工具栏
    def _create_toolbar(self):
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # 后退按钮
        back_action = QAction('← 后退', self)
        back_action.triggered.connect(self.web_engine.go_back)
        toolbar.addAction(back_action)

        # 前进按钮
        forward_action = QAction('前进 →', self)
        forward_action.triggered.connect(self.web_engine.go_forward)
        toolbar.addAction(forward_action)

        # 刷新按钮
        refresh_action = QAction('⟳ 刷新', self)
        refresh_action.triggered.connect(self.web_engine.reload)
        toolbar.addAction(refresh_action)

        toolbar.addSeparator()

        # 访问新地址按钮
        goto_action = QAction('🔗 访问新地址', self)
        goto_action.triggered.connect(self._goto_url)
        toolbar.addAction(goto_action)

        # 多开按钮
        new_window_action = QAction('➕ 新窗口', self)
        new_window_action.triggered.connect(self._new_window)
        toolbar.addAction(new_window_action)

    def _goto_url(self):
        current_url = self.web_engine.get_view().url().toString()
        display_url = current_url.replace('https://', '').replace('http://', '')

        text, ok = QInputDialog.getText(
            self, '访问新地址', '请输入网址:',
            QLineEdit.Normal, display_url
        )
        if ok and text.strip():
            url = text.strip()
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            self.web_engine.load(url)

    def _new_window(self):
        new_window = BrowserWindow()
        new_window.show()

    def _connect_signals(self):
        view = self.web_engine.get_view()

        # 页面加载进度
        view.loadProgress.connect(self.progress_bar.setValue)

        # 页面加载完成
        view.loadFinished.connect(self._on_load_finished)

        # 页面标题变化
        view.titleChanged.connect(self._on_title_changed)

        # URL变化
        view.urlChanged.connect(self._on_url_changed)

    def _on_load_finished(self, success: bool):
        self.progress_bar.setValue(100)
        if success:
            self.status_bar.showMessage('加载完成')
        else:
            self.status_bar.showMessage('加载失败')

    def _on_title_changed(self, title: str):
        pass

    def _on_url_changed(self, url):
        url_str = url.toString()
        self.status_bar.showMessage(f'正在访问: {url_str}')
        display_url = url_str.replace('https://', '').replace('http://', '')
        self.url_label.setText(display_url)

    def set_url(self, url: str):
        self.web_engine.load(url)

    # 拦截关闭事件
    def closeEvent(self, event):
        pass
