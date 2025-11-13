"""FastAPI main application"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from sqlalchemy import select

from database import create_tables
from routes import auth_routes, bot_routes
from websocket_manager import ws_manager
from bot_manager import bot_manager
from auth import SECRET_KEY, ALGORITHM
from jose import JWTError, jwt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    import os
    port = os.getenv("PORT", "8000")
    logger.info(f"Starting up on port {port}...")

    try:
        await create_tables()
        logger.info("Database tables created")
        bot_manager.set_ws_manager(ws_manager)
        logger.info("Bot manager initialized")
        logger.info(f"Application started successfully on port {port}")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down...")
    try:
        await bot_manager.stop_all()
        logger.info("All bots stopped")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")
    logger.info("Application shut down successfully")


# Create FastAPI app
app = FastAPI(
    title="Prediction Arbitrage Bot API",
    description="Multi-platform prediction market arbitrage bot with real-time WebSocket updates",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_routes.router)
app.include_router(bot_routes.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Prediction Arbitrage Bot API",
        "version": "2.0.0",
        "docs": "/docs",
        "platforms": ["Polymarket", "Kalshi", "Opinion.trade"]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    import os
    return {
        "status": "healthy",
        "port": os.getenv("PORT", "8000"),
        "version": "2.0.0"
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    """WebSocket endpoint for real-time updates"""
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return

    try:
        # Verify token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            await websocket.close(code=1008, reason="Invalid token")
            return

        # Get user from database
        from database import async_session, users

        async with async_session() as session:
            result = await session.execute(select(users).where(users.c.email == email))
            user_row = result.first()
            user = dict(user_row._mapping) if user_row else None

        if not user:
            await websocket.close(code=1008, reason="User not found")
            return

        user_id = user["id"]

        # Connect WebSocket
        await ws_manager.connect(websocket, user_id)

        try:
            # Send welcome message
            await websocket.send_json({
                "type": "connected",
                "data": {"message": f"Connected as {user['username']}"}
            })

            # Keep connection alive and receive messages
            while True:
                data = await websocket.receive_text()
                # Echo back (can be used for heartbeat)
                await websocket.send_json({
                    "type": "pong",
                    "data": {"message": "pong"}
                })

        except WebSocketDisconnect:
            ws_manager.disconnect(websocket, user_id)
            logger.info(f"WebSocket disconnected for user {user_id}")

    except JWTError:
        await websocket.close(code=1008, reason="Invalid token")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1011, reason="Internal error")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
