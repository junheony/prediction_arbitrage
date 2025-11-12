"""
Dashboard API Server
대시보드용 FastAPI + WebSocket 서버
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from decimal import Decimal

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===========================
# FastAPI 앱 초기화
# ===========================

app = FastAPI(
    title="Prediction Arbitrage Dashboard API",
    description="차익거래 봇 대시보드 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===========================
# 데이터 모델
# ===========================

class BotStatus(BaseModel):
    running: bool
    active_positions: int
    total_exposure: float
    today_profit: float
    opportunities_count: int

class Settings(BaseModel):
    min_profit: float
    max_risk: float
    max_position: int
    scan_interval: int
    active_platforms: List[str]

class BotResponse(BaseModel):
    success: bool
    message: str

# ===========================
# 글로벌 상태
# ===========================

class BotState:
    """봇 상태 관리"""
    def __init__(self):
        self.running = False
        self.active_positions = []
        self.opportunities = []
        self.logs = []
        self.settings = {
            'min_profit': 1.0,
            'max_risk': 0.3,
            'max_position': 10000,
            'scan_interval': 60,
            'active_platforms': ['polymarket', 'kalshi', 'manifold']
        }
        self.stats = {
            'total_exposure': 0,
            'today_profit': 0,
            'opportunities_count': 0
        }

bot_state = BotState()

# WebSocket 연결 관리
class ConnectionManager:
    """WebSocket 연결 관리자"""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket connection. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """모든 연결된 클라이언트에 메시지 전송"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")

manager = ConnectionManager()

# ===========================
# API 엔드포인트
# ===========================

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "Prediction Arbitrage Dashboard API",
        "version": "1.0.0",
        "status": "running"
    }

@app.post("/api/bot/start", response_model=BotResponse)
async def start_bot():
    """봇 시작"""
    if bot_state.running:
        return BotResponse(success=False, message="봇이 이미 실행 중입니다")

    bot_state.running = True

    # WebSocket을 통해 상태 브로드캐스트
    await manager.broadcast({
        "type": "status_update",
        "status": {
            "running": True,
            "active_positions": len(bot_state.active_positions),
            "total_exposure": bot_state.stats['total_exposure'],
            "today_profit": bot_state.stats['today_profit'],
            "opportunities_count": bot_state.stats['opportunities_count']
        }
    })

    # 로그 전송
    await manager.broadcast({
        "type": "log",
        "log": {
            "message": "봇이 시작되었습니다",
            "level": "success"
        }
    })

    logger.info("Bot started")
    return BotResponse(success=True, message="봇이 성공적으로 시작되었습니다")

@app.post("/api/bot/stop", response_model=BotResponse)
async def stop_bot():
    """봇 정지"""
    if not bot_state.running:
        return BotResponse(success=False, message="봇이 실행 중이 아닙니다")

    bot_state.running = False

    # WebSocket을 통해 상태 브로드캐스트
    await manager.broadcast({
        "type": "status_update",
        "status": {
            "running": False,
            "active_positions": len(bot_state.active_positions),
            "total_exposure": bot_state.stats['total_exposure'],
            "today_profit": bot_state.stats['today_profit'],
            "opportunities_count": bot_state.stats['opportunities_count']
        }
    })

    # 로그 전송
    await manager.broadcast({
        "type": "log",
        "log": {
            "message": "봇이 정지되었습니다",
            "level": "warning"
        }
    })

    logger.info("Bot stopped")
    return BotResponse(success=True, message="봇이 정지되었습니다")

@app.get("/api/data/refresh")
async def refresh_data():
    """데이터 새로고침"""
    # 현재 상태 반환
    data = {
        "status": {
            "running": bot_state.running,
            "active_positions": len(bot_state.active_positions),
            "total_exposure": bot_state.stats['total_exposure'],
            "today_profit": bot_state.stats['today_profit'],
            "opportunities_count": len(bot_state.opportunities)
        },
        "opportunities": bot_state.opportunities,
        "positions": bot_state.active_positions,
        "chart_data": {
            "profit": {
                "labels": generate_time_labels(),
                "data": generate_profit_data()
            },
            "risk": {
                "data": [35000, 5000, 7500, 2500]
            }
        }
    }

    return data

@app.post("/api/settings/update", response_model=BotResponse)
async def update_settings(settings: Settings):
    """설정 업데이트"""
    bot_state.settings = settings.dict()

    # WebSocket을 통해 로그 전송
    await manager.broadcast({
        "type": "log",
        "log": {
            "message": f"설정이 업데이트되었습니다: 최소 수익률 {settings.min_profit}%",
            "level": "info"
        }
    })

    logger.info(f"Settings updated: {settings}")
    return BotResponse(success=True, message="설정이 저장되었습니다")

@app.get("/api/data/export")
async def export_data():
    """데이터 내보내기 (CSV)"""
    # CSV 데이터 생성
    csv_data = generate_csv_export()

    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=arbitrage-data-{datetime.now().strftime('%Y%m%d')}.csv"
        }
    )

# ===========================
# WebSocket 엔드포인트
# ===========================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 연결"""
    await manager.connect(websocket)

    try:
        # 초기 데이터 전송
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket 연결 성공"
        })

        # 데모 데이터 전송 (실제 환경에서는 실시간 데이터)
        demo_data = get_demo_data()
        await websocket.send_json(demo_data)

        # 주기적으로 업데이트 전송
        asyncio.create_task(send_periodic_updates(websocket))

        # 메시지 수신 대기
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received WebSocket message: {data}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket disconnected")

async def send_periodic_updates(websocket: WebSocket):
    """주기적으로 업데이트 전송"""
    try:
        while True:
            await asyncio.sleep(5)  # 5초마다

            # 랜덤 데이터 업데이트 (데모용)
            if bot_state.running:
                bot_state.stats['today_profit'] += 0.5
                bot_state.stats['opportunities_count'] = len(bot_state.opportunities)

                await websocket.send_json({
                    "type": "status_update",
                    "status": {
                        "running": bot_state.running,
                        "active_positions": len(bot_state.active_positions),
                        "total_exposure": bot_state.stats['total_exposure'],
                        "today_profit": round(bot_state.stats['today_profit'], 2),
                        "opportunities_count": bot_state.stats['opportunities_count']
                    }
                })
    except Exception as e:
        logger.error(f"Error in periodic updates: {e}")

# ===========================
# 헬퍼 함수
# ===========================

def get_demo_data():
    """데모 데이터 생성"""
    return {
        "type": "initial_data",
        "status": {
            "running": True,
            "active_positions": 3,
            "total_exposure": 15000,
            "today_profit": 234.56,
            "opportunities_count": 12
        },
        "opportunities": [
            {
                "platform1": "polymarket",
                "platform2": "kalshi",
                "question": "Will Bitcoin reach $100,000 by end of 2025?",
                "profit": 2.3,
                "confidence": 85,
                "risks": ["Low liquidity", "Resolution difference"]
            },
            {
                "platform1": "kalshi",
                "platform2": "manifold",
                "question": "Will inflation be below 3% in Q1 2025?",
                "profit": 1.8,
                "confidence": 92,
                "risks": []
            }
        ],
        "positions": [
            {
                "platform1": "polymarket",
                "platform2": "kalshi",
                "investment": 5000,
                "expected_profit": 115,
                "entry_time": datetime.now().isoformat()
            }
        ],
        "chart_data": {
            "profit": {
                "labels": ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00"],
                "data": [0, 45, 89, 134, 189, 234]
            },
            "risk": {
                "data": [35000, 5000, 7500, 2500]
            }
        }
    }

def generate_time_labels():
    """시간 라벨 생성"""
    now = datetime.now()
    labels = []
    for i in range(6):
        time = now.replace(hour=9+i, minute=0)
        labels.append(time.strftime("%H:%M"))
    return labels

def generate_profit_data():
    """수익 데이터 생성"""
    return [0, 45, 89, 134, 189, round(bot_state.stats['today_profit'], 2)]

def generate_csv_export():
    """CSV 내보내기 데이터 생성"""
    csv = "timestamp,platform1,platform2,profit_percent,confidence,status\n"

    for opp in bot_state.opportunities:
        csv += f"{datetime.now().isoformat()},{opp['platform1']},{opp['platform2']},{opp['profit']},{opp['confidence']},active\n"

    return csv

# ===========================
# 메인 실행
# ===========================

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║        🌐 DASHBOARD API SERVER 🌐                           ║
    ║                                                              ║
    ║  포트: 8080                                                  ║
    ║  대시보드: http://localhost:8080                            ║
    ║  API 문서: http://localhost:8080/docs                       ║
    ║  WebSocket: ws://localhost:8080/ws                          ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info"
    )
