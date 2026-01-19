@echo off
chcp 65001 >nul
cd /d "%~dp0cmd"
python main.py
pause
