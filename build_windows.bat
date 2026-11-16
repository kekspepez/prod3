@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Student Desk - build EXE
echo ==========================================
echo       Сборка Student Desk для Windows
echo ==========================================

rem --- ищем Python: сначала py-лаунчер, потом python ---
set "PY="
py -3 --version >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if not defined PY (
  python --version >nul 2>&1
  if not errorlevel 1 set "PY=python"
)
if not defined PY (
  echo Python не найден. Установи Python 3.11 или новее с python.org
  echo и включи опцию Add Python to PATH.
  pause
  exit /b 1
)
echo Используется: %PY%

if not exist "student_desk.py" (
  echo Не найден student_desk.py. Распакуй архив целиком и запусти файл из папки проекта.
  pause
  exit /b 1
)

rem --- отдельное окружение, чтобы не конфликтовать с другими пакетами ---
if not exist ".venv\Scripts\python.exe" (
  %PY% -m venv .venv
  if errorlevel 1 goto :fail
)
set "VPY=.venv\Scripts\python.exe"

"%VPY%" -m pip install --upgrade pip
if errorlevel 1 goto :fail
"%VPY%" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

"%VPY%" -m PyInstaller --noconfirm --clean --windowed --name StudentDesk --icon "assets\student_desk_logo.ico" --add-data "assets;assets" student_desk.py
if errorlevel 1 goto :fail

echo.
echo Готово! EXE находится в папке dist\StudentDesk\
pause
exit /b 0

:fail
echo.
echo Сборка завершилась с ошибкой. Проверь сообщения выше.
pause
exit /b 1
