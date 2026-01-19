# Web引擎视图
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtWidgets import QApplication


# 伪装 User Agent
FAKE_USER_AGENT = (
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; Win64; x64; Trident/7.0; .NET4.0C; .NET4.0E)"
)


# Web引擎视图类
class WebEngine:
    def __init__(self, parent=None):
        self.view = QWebEngineView(parent)
        self.view.setContextMenuPolicy(Qt.NoContextMenu)  # 禁用右键菜单
        self._setup_settings()
        self._spoof_user_agent()

    def _setup_settings(self):
        # 配置Web引擎
        settings = self.view.page().settings()
        settings.setAttribute(
            settings.JavascriptEnabled, True
        )
        settings.setAttribute(
            settings.LocalStorageEnabled, True
        )
        # 禁用硬件加速和WebGL，避免崩溃
        settings.setAttribute(
            settings.Accelerated2dCanvasEnabled, False
        )
        settings.setAttribute(
            settings.WebGLEnabled, False
        )

    # 伪装 User Agent
    def _spoof_user_agent(self):
        profile = self.view.page().profile()
        profile.setHttpUserAgent(FAKE_USER_AGENT)

    def load(self, url: str):
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        self.view.load(QUrl(url))

    def reload(self):
        self.view.reload()

    def go_back(self):
        self.view.back()

    def go_forward(self):
        self.view.forward()

    def stop(self):
        self.view.stop()

    def get_view(self):
        return self.view

    def set_parent(self, parent):
        self.view.setParent(parent)
