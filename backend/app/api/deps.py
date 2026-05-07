"""
Authentication dependencies and current user retrieval.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

async def get_current_user(
    db: AsyncSession = Depends(get_db)
) -> User:
    # ── DEBUG: NO AUTH ───────────────────────────────────────────────────────
    # Always return a default demo user to bypass login
    email = "demo@example.com"
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(
            email=email,
            username="demo_user",
            password_hash="disabled",
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    return user
