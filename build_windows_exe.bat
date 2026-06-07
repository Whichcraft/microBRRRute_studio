@echo off
setlocal
cd /d %~dp0
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
py -m PyInstaller --noconfirm --onefile --windowed --name microBRRRute_Studio main.py
echo.
echo Built executable: dist\microBRRRute_Studio.exe
pause
