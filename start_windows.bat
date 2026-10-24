@echo off
cd /d "%~dp0"
set TCC_LOCAL_MODE=1
py -m streamlit run app.py
pause
