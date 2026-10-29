@echo off
REM Build dist\Detent\Detent.exe (folder build: starts fast at login) and the installer if Inno Setup is installed.
REM Run from this folder on Windows.
py -m pip install -r requirements.txt pyinstaller || goto :err
py make_icon.py || goto :err
py -m PyInstaller --noconfirm --clean --onedir --noconsole --name Detent --icon detent.ico ^
  --hidden-import pystray._win32 app.py || goto :err
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
  "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" installer.iss || goto :err
  echo Installer: Output\Detent-Setup.exe
) else (
  echo Inno Setup not found - portable app is in dist\Detent\  ^(run Detent.exe inside it^)
)
exit /b 0
:err
echo BUILD FAILED
exit /b 1
