@echo off
echo Activating virtual environment and starting server...
call .\venv\Scripts\activate.bat
uvicorn app.main:app --reload
