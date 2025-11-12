"""Pydantic models for API requests and responses"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime


# Auth models
class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# Bot models
class BotConfig(BaseModel):
    min_profit_threshold: float = Field(default=0.01, ge=0.001, le=1.0)
    max_position_size: float = Field(default=100.0, ge=1.0, le=10000.0)
    platforms: list[str] = Field(default=["polymarket", "kalshi", "opinion"])
    auto_execute: bool = False
    notification_enabled: bool = True


class BotStartRequest(BaseModel):
    config: Optional[BotConfig] = None


class BotStatus(BaseModel):
    status: str  # running, stopped, error
    started_at: Optional[datetime] = None
    opportunities_found: int = 0
    total_profit: str = "0.0"
    config: Optional[Dict[str, Any]] = None


class ArbitrageOpportunity(BaseModel):
    id: Optional[int] = None
    platform_a: str
    platform_b: str
    market_a: str
    market_b: str
    profit_percentage: str
    suggested_action: str
    timestamp: datetime
    executed: bool = False


# WebSocket models
class WSMessage(BaseModel):
    type: str  # opportunity, status, error
    data: Dict[str, Any]
