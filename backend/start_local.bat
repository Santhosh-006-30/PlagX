@echo off
setlocal enabledelayedexpansion
echo [PlagX] Starting Local Environment (No Docker)

:: Ensure we are in the backend directory
if not exist "app" (
    if exist "backend" (
        cd backend
    ) else (
        echo [ERROR] Could not find backend directory or app folder.
        pause
        exit /b
    )
)

echo [PlagX] Checking dependencies...
python -m pip install -r requirements.txt

echo [PlagX] Checking NLP Models...
python -m spacy download en_core_web_sm

echo [PlagX] Initializing Database...
echo import asyncio > init_db.py
echo from app.database import Base, engine >> init_db.py
echo from app.models.user import User >> init_db.py
echo from app.models.document import Document >> init_db.py
echo from app.models.scan import ScanJob >> init_db.py
echo async def init(): >> init_db.py
echo     async with engine.begin() as conn: >> init_db.py
echo         await conn.run_sync(Base.metadata.create_all) >> init_db.py
echo asyncio.run(init()) >> init_db.py

python init_db.py
del init_db.py

echo [PlagX] Launching API Server (Port 8000)...
start "PlagX API" cmd /k "python -m uvicorn app.main:app --reload --port 8000"

echo [PlagX] Launching Celery Worker...
start "PlagX Worker" cmd /k "python -m celery -A app.celery_worker.celery_app worker --loglevel=info -P solo"

echo [PlagX] System is starting up. 
echo API: http://localhost:8000
echo Frontend (if running): http://localhost:3000
pause
