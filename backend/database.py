"""Database configuration and models"""
import sqlalchemy
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./arbitrage_bot.db")

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)

# Create async session factory
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

metadata = sqlalchemy.MetaData()
Base = declarative_base()

# Users table
users = sqlalchemy.Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("email", String, unique=True, index=True, nullable=False),
    Column("username", String, unique=True, index=True, nullable=False),
    Column("hashed_password", String, nullable=False),
    Column("is_active", Boolean, default=True),
    Column("created_at", DateTime, default=datetime.utcnow),
)

# Bot sessions table
bot_sessions = sqlalchemy.Table(
    "bot_sessions",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("user_id", Integer, nullable=False),
    Column("status", String, default="stopped"),  # running, stopped, error
    Column("config", JSON, nullable=True),
    Column("started_at", DateTime, nullable=True),
    Column("stopped_at", DateTime, nullable=True),
    Column("opportunities_found", Integer, default=0),
    Column("total_profit", String, default="0.0"),
)

# Arbitrage opportunities table
opportunities = sqlalchemy.Table(
    "opportunities",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("user_id", Integer, nullable=False),
    Column("platform_a", String, nullable=False),
    Column("platform_b", String, nullable=False),
    Column("market_a", String, nullable=False),
    Column("market_b", String, nullable=False),
    Column("profit_percentage", String, nullable=False),
    Column("suggested_action", String, nullable=False),
    Column("timestamp", DateTime, default=datetime.utcnow),
    Column("executed", Boolean, default=False),
)

async def create_tables():
    """Create all tables"""
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)

async def get_db():
    """Get database session"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
