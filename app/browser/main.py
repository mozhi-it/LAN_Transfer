import sys
import re
import traceback
import ctypes
import ctypes.wintypes

from PyQt5.QtWidgets import QApplication, QDialog, QLineEdit, QVBoxLayout, QLabel, QPushButton, QMessageBox
from PyQt5.QtCore import Qt

try:
    from .browser_window import BrowserWindow
except ImportError:
    from browser_window import BrowserWindow


# Windows API常量
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_SET_QUOTA = 0x0100
PROCESS_TERMINATE = 0x0001
PROCESS_ALL_ACCESS = 0x1F0FFF
TOKEN_ADJUST_PRIVILEGES = 0x20
SE_PRIVILEGE_ENABLED = 0x2


# 启用进程保护
def enable_process_protection():
    try:
        kernel32 = ctypes.windll.kernel32
        advapi32 = ctypes.windll.advapi32
        # 启用SeDebugPrivilege权限
        token_handle = ctypes.wintypes.HANDLE()
        if advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), TOKEN_ADJUST_PRIVILEGES, ctypes.byref(token_handle)):
            luid = ctypes.wintypes.LUID()
            if advapi32.LookupPrivilegeValueW(None, "SeDebugPrivilege", ctypes.byref(luid)):
                privileges = ctypes.wintypes.LUID_AND_ATTRIBUTES()
                privileges.Luid = luid
                privileges.Attributes = SE_PRIVILEGE_ENABLED
                priv_list = (ctypes.wintypes.LUID_AND_ATTRIBUTES * 1)(privileges)
                advapi32.AdjustTokenPrivileges(token_handle, False, priv_list, 0, None, None)
            kernel32.CloseHandle(token_handle)
        # 获取自身进程句柄并锁定，防止被TerminateProcess
        proc_handle = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, kernel32.GetCurrentProcessId())
        if proc_handle:
            kernel32.CloseHandle(proc_handle)
    except Exception:
        pass


# IPv4地址正则表达式
IP_PATTERN = re.compile(
    r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
    r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'
    r'(?::\d{1,5})?$'
)


# 检查ip地址是否填写正确
def is_valid_ip(ip: str) -> bool:
    match = IP_PATTERN.match(ip)
    if not match:
        return False
    full_match = match.group(0)
    if ':' in full_match:
        port_str = full_match.split(':')[-1]
        port = int(port_str)
        if port == 0 or port > 65535:
            return False
    return True


class UrlInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('LAN Transfer Web客户端连接程序')
        self.setFixedSize(400, 150)
        self.url = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        label = QLabel('请输入LAN Transfer服务端IP地址:')
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('如192.168.1.100:5000')
        self.url_input.setText('')
        layout.addWidget(self.url_input)

        layout.addSpacing(10)
        confirm_btn = QPushButton('连接')
        confirm_btn.setFixedHeight(35)
        confirm_btn.clicked.connect(self._on_confirm)
        layout.addWidget(confirm_btn)

        self.setTabOrder(self.url_input, confirm_btn)

    def _on_confirm(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, '警告', '请输入IP地址')
            return
        if not is_valid_ip(url):
            QMessageBox.warning(self, '警告', '请输入有效的IP地址')
            return
        self.url = url
        self.accept()

    def get_url(self):
        return 'http://' + self.url


# 运行浏览器
def run_browser():
    # 全局异常处理器
    def exception_handler(exc_type, exc_value, exc_traceback):
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(f"程序发生异常:\n{error_msg}")
        QMessageBox.critical(
            None, '错误',
            f"程序发生错误:\n{exc_value}\n\n详细信息已打印到控制台。"
        )
        sys.exit(1)

    sys.excepthook = exception_handler
    app = QApplication(sys.argv)

    # 进程保护
    enable_process_protection()

    # 伪装应用程序信息
    app.setApplicationName("TextEditor")
    app.setApplicationDisplayName("Text Editor")
    app.setOrganizationName("Microsoft")

    dialog = UrlInputDialog()
    if dialog.exec_() != QDialog.Accepted:
        sys.exit(0)

    # 获取URL并打开浏览器
    url = dialog.get_url()
    window = BrowserWindow(start_url=url)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    run_browser()
