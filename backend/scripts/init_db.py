import asyncio
import sys
import os

# Add the parent directory to sys.path to import 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, Base
from app.models import User, Document, ScanJob, RefreshToken, AuditLog, Fingerprint, HighlightRegion, StylometryMetric

async def init_db():
    print("Initializing local SQLite database...")
    async with engine.begin() as conn:
        # This will create all tables defined in models
        await conn.run_sync(Base.metadata.create_all)
    print("Database initialized successfully at ./plagx.db")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_db())
