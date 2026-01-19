"""Simple Browser - 基于PyQt5的简易浏览器"""

from .main import run_browser
from .browser_window import BrowserWindow
from .web_engine import WebEngine

__all__ = ['run_browser', 'BrowserWindow', 'WebEngine']
