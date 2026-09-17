@echo off
echo Este arquivo e opcional. A compilacao principal pode ser feita pelo GitHub Actions.
python -m pip install --upgrade pip
pip install -r requirements.txt
pyinstaller --clean --noconfirm MaquinaDoTempoAudio.spec
echo.
echo Pronto. Veja a pasta dist.
pause
