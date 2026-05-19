@echo off
setlocal enabledelayedexpansion
set PYTHON=C:\Python34\python.exe
set PROGRAMFILE=vanguard_gui.py
set FOLDERNAME=vanguard-bandits-psx-tools

set VERSION=
for /f "tokens=2 delims=^= " %%a in ('findstr "MAIN_VERSION" %PROGRAMFILE% 2^>nul') do (
    if not defined VERSION (
        set VERSION=%%a
        set VERSION=!VERSION:"=!
    )
)
if not defined VERSION set VERSION=0.0.0
set RELEASE_DIR=%FOLDERNAME%-%VERSION%-winxp-32

echo %FOLDERNAME% v%VERSION%

rmdir /s /q build dist __pycache__ 2>nul
del /s /q *.pyc *.spec *.manifest 2>nul
rmdir /s /q "%RELEASE_DIR%" 2>nul

%PYTHON% -m PyInstaller --onefile --noupx --noconsole %PROGRAMFILE%

rename dist "%RELEASE_DIR%"
xcopy "tools\*" "%RELEASE_DIR%\tools\" /E /Y >nul 2>nul

rmdir /s /q build __pycache__ 2>nul
del /s /q *.pyc *.spec *.manifest 2>nul

echo.
echo DONE! %RELEASE_DIR%
echo.
pause