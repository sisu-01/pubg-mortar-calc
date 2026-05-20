@echo off
:: 1. 배치 파일이 있는 현재 프로젝트 폴더 위치로 이동
cd /d "%~dp0"

:: 2. 프로젝트 폴더 내 .venv 가상환경 활성화 (핵심!)
call .venv\Scripts\activate

:: 3. 가상환경이 켜진 상태에서 파이썬 실행
python main.py
pause