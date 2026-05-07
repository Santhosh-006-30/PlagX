import asyncio
from app.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash

async def create_test_user():
    async with AsyncSessionLocal() as db:
        # Check if user already exists
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.email == "test@example.com"))
        if result.scalar_one_or_none():
            print("Test user already exists.")
            return

        test_user = User(
            email="test@example.com",
            username="testuser",
            password_hash=get_password_hash("password123"),
            is_active=True
        )
        db.add(test_user)
        await db.commit()
        print("Test user created successfully!")
        print("Email: test@example.com")
        print("Password: password123")

if __name__ == "__main__":
    asyncio.run(create_test_user())
