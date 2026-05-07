# PlagX Plagiarism API

FastAPI backend for a plagiarism detection system.

## Features
- JWT Authentication (Register/Login)
- File Upload (PDF, DOCX, TXT)
- Text Extraction Service
- Document Management
- Scan Job Orchestration (Placeholder for ML)
- Structured Logging
- PostgreSQL Integration (SQLAlchemy Async)
- Containerized with Docker

## Setup

### Local Setup
1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and configure variables.
4. Run the app:
   ```bash
   uvicorn app.main:app --reload
   ```

### Docker Setup
1. Run with Docker Compose:
   ```bash
   docker-compose up --build
   ```

## API Documentation
Once the app is running, visit:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Project Structure
```
backend/
├── app/
│   ├── api/          # Route handlers and dependencies
│   ├── core/         # Security, config, logging
│   ├── models/       # SQLAlchemy models
│   ├── schemas/      # Pydantic schemas
│   ├── services/     # Business logic (extraction, etc.)
│   ├── database.py   # DB connection setup
│   └── main.py       # FastAPI app entry point
├── Dockerfile
├── docker-compose.yaml
└── requirements.txt
```
