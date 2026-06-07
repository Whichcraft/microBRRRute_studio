@echo off
setlocal
cd /d %~dp0
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
py -m PyInstaller --noconfirm --onefile --windowed --name MBSEQ_Studio main.py
echo.
echo Built executable: dist\MBSEQ_Studio.exe
pause
