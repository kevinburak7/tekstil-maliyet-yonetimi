@echo off
REM Tekstil Maliyet - tek dosya EXE derleme
python -m pip install -r requirements.txt pyinstaller --quiet
python -m PyInstaller --noconfirm TekstilMaliyetYonetimi.spec
echo.
echo Cikti: dist\TekstilMaliyetYonetimi.exe
