"""Database configuration and models"""
import databases
import sqlalchemy
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./arbitrage_bot.db")

database = databases.Database(DATABASE_URL)
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

# Create engine
engine = sqlalchemy.create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

def create_tables():
    """Create all tables"""
    metadata.create_all(engine)

async def connect_db():
    """Connect to database"""
    await database.connect()

async def disconnect_db():
    """Disconnect from database"""
    await database.disconnect()
