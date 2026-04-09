@echo off
setlocal enabledelayedexpansion
set PYTHON=C:\Python34\python.exe
set PROGRAMFILE=def-of-oas-text-processor.pyw
set FOLDERNAME=def-of-oas-text-processor

set VERSION=
for /f "tokens=2 delims=^= " %%a in ('findstr "MAIN_VERSION" %PROGRAMFILE% 2^>nul') do (
    if not defined VERSION (
        set VERSION=%%a
        set VERSION=!VERSION:"=!
    )
)
if not defined VERSION set VERSION=0.4
set RELEASE_DIR=%FOLDERNAME%-%VERSION%

echo %FOLDERNAME% v%VERSION%

rmdir /s /q build dist __pycache__ 2>nul
del /s /q *.pyc *.spec *.manifest 2>nul
rmdir /s /q "%RELEASE_DIR%" 2>nul

REM %PYTHON% -m PyInstaller --onefile --noconsole --add-data "widths.txt;." --add-data "widths-template.txt;." %PROGRAMFILE%
%PYTHON% -m PyInstaller --onefile --noconsole %PROGRAMFILE%

rename dist "%RELEASE_DIR%"
REM copy "widths.txt" "%RELEASE_DIR%\" >nul 2>nul
REM copy "widths-template.txt" "%RELEASE_DIR%\" >nul 2>nul

rmdir /s /q build __pycache__ 2>nul
del /s /q *.pyc *.spec *.manifest 2>nul

echo.
echo DONE! %RELEASE_DIR%
echo.
pause