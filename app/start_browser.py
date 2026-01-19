# 启动脚本

import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
from browser import run_browser

if __name__ == '__main__':
    run_browser()
