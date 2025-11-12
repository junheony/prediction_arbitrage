"""
Delta Hedge System & API
델타헤지 시스템 및 원클릭 API
"""

import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal
import logging
import uvicorn

logger = logging.getLogger(__name__)

# ===========================
# 데이터 모델 (Pydantic)
# ===========================

class Position(BaseModel):
    """포지션 정보"""
    position_id: str
    market_a_id: str
    market_b_id: str
    platform_a: str
    platform_b: str
    side_a: str  # 'yes' or 'no'
    side_b: str
    size: float
    entry_price_a: float
    entry_price_b: float
    current_price_a: Optional[float] = None
    current_price_b: Optional[float] = None
    pnl: Optional[float] = None
    is_hedged: bool = False
    created_at: datetime

class HedgeRequest(BaseModel):
    """헤지 요청"""
    position_id: str
    hedge_type: str  # 'full', 'partial', 'auto'
    hedge_percentage: Optional[float] = 100.0  # 헤지 비율
    target_platform: Optional[str] = None  # 특정 플랫폼 지정

class HedgeResult(BaseModel):
    """헤지 결과"""
    success: bool
    position_id: str
    hedge_orders: List[Dict]
    total_cost: float
    estimated_locked_profit: float
    execution_time: float
    message: str

class DashboardData(BaseModel):
    """대시보드 데이터"""
    active_positions: int
    total_pnl: float
    hedged_positions: int
    pending_hedges: int
    opportunities: List[Dict]
    recent_trades: List[Dict]
    alerts: List[Dict]

# ===========================
# 델타헤지 엔진
# ===========================

@dataclass
class HedgeStrategy:
    """헤지 전략"""
    strategy_type: str  # 'full', 'partial', 'dynamic'
    target_platforms: List[str]
    execution_method: str  # 'market', 'limit', 'twap'
    slippage_tolerance: Decimal
    max_cost: Decimal

class DeltaHedgeEngine:
    """델타헤지 실행 엔진"""

    def __init__(
        self,
        platform_clients: Dict,
        position_manager
    ):
        self.clients = platform_clients
        self.position_manager = position_manager
        self.pending_hedges = {}
        self.hedge_history = []

    async def calculate_hedge(
        self,
        position: Position,
        hedge_percentage: float = 100.0
    ) -> Dict:
        """
        헤지 계산

        Args:
            position: 포지션 정보
            hedge_percentage: 헤지 비율 (100% = 완전 헤지)

        Returns:
            헤지 계획
        """

        # 현재 포지션 분석
        current_exposure = {
            'platform_a': {
                'platform': position.platform_a,
                'market_id': position.market_a_id,
                'side': position.side_a,
                'size': position.size,
                'entry_price': position.entry_price_a,
                'current_price': position.current_price_a or position.entry_price_a
            },
            'platform_b': {
                'platform': position.platform_b,
                'market_id': position.market_b_id,
                'side': position.side_b,
                'size': position.size,
                'entry_price': position.entry_price_b,
                'current_price': position.current_price_b or position.entry_price_b
            }
        }

        # 헤지 크기 계산
        hedge_size = Decimal(str(position.size)) * Decimal(str(hedge_percentage / 100))

        # 반대 포지션 계산
        hedge_orders = []

        for key, exposure in current_exposure.items():
            # 현재 포지션의 반대 방향
            hedge_side = 'no' if exposure['side'] == 'yes' else 'yes'

            # 예상 헤지 비용
            current_price = Decimal(str(exposure['current_price']))
            hedge_cost = hedge_size * (Decimal('1.0') - current_price if exposure['side'] == 'yes' else current_price)

            hedge_order = {
                'platform': exposure['platform'],
                'market_id': exposure['market_id'],
                'side': hedge_side,
                'size': float(hedge_size),
                'estimated_price': float(Decimal('1.0') - current_price if exposure['side'] == 'yes' else current_price),
                'estimated_cost': float(hedge_cost),
                'execution_type': 'market'
            }

            hedge_orders.append(hedge_order)

        # 총 헤지 비용
        total_hedge_cost = sum(Decimal(str(order['estimated_cost'])) for order in hedge_orders)

        # 현재 PnL
        current_pnl = self._calculate_pnl(position)

        # 헤지 후 잠긴 수익
        locked_profit = current_pnl - float(total_hedge_cost)

        return {
            'hedge_orders': hedge_orders,
            'total_hedge_cost': float(total_hedge_cost),
            'current_pnl': current_pnl,
            'estimated_locked_profit': locked_profit,
            'hedge_percentage': hedge_percentage,
            'recommendation': 'execute' if locked_profit > 0 else 'hold'
        }

    async def execute_hedge(
        self,
        position: Position,
        hedge_plan: Dict,
        execute_immediately: bool = True
    ) -> HedgeResult:
        """
        헤지 실행

        Args:
            position: 포지션
            hedge_plan: 헤지 계획
            execute_immediately: 즉시 실행 여부

        Returns:
            헤지 결과
        """

        start_time = datetime.now()
        executed_orders = []
        total_cost = Decimal('0')

        try:
            # 각 헤지 주문 실행
            for hedge_order in hedge_plan['hedge_orders']:
                platform = hedge_order['platform']
                client = self.clients.get(platform)

                if not client:
                    raise ValueError(f"Client not found for platform: {platform}")

                # 주문 실행
                result = await self._execute_hedge_order(client, hedge_order)

                if result['status'] == 'filled':
                    executed_orders.append(result)
                    total_cost += Decimal(str(result['filled_cost']))
                else:
                    # 일부 실패 시 롤백 고려
                    logger.warning(f"Hedge order failed: {result}")

            # 포지션 업데이트
            position.is_hedged = True
            await self.position_manager.update_position(position)

            # 기록
            self.hedge_history.append({
                'position_id': position.position_id,
                'timestamp': datetime.now(),
                'hedge_orders': executed_orders,
                'total_cost': float(total_cost)
            })

            execution_time = (datetime.now() - start_time).total_seconds()

            return HedgeResult(
                success=True,
                position_id=position.position_id,
                hedge_orders=executed_orders,
                total_cost=float(total_cost),
                estimated_locked_profit=hedge_plan['estimated_locked_profit'],
                execution_time=execution_time,
                message=f"Hedge executed successfully in {execution_time:.2f}s"
            )

        except Exception as e:
            logger.error(f"Hedge execution failed: {e}")
            return HedgeResult(
                success=False,
                position_id=position.position_id,
                hedge_orders=executed_orders,
                total_cost=float(total_cost),
                estimated_locked_profit=0.0,
                execution_time=(datetime.now() - start_time).total_seconds(),
                message=f"Hedge failed: {str(e)}"
            )

    async def _execute_hedge_order(self, client, hedge_order: Dict) -> Dict:
        """개별 헤지 주문 실행"""

        try:
            # 플랫폼별 주문 실행
            if hasattr(client, 'place_market_order'):
                result = await client.place_market_order(
                    market_id=hedge_order['market_id'],
                    side='buy' if hedge_order['side'] == 'yes' else 'sell',
                    size=hedge_order['size']
                )
            else:
                result = await client.place_order(
                    market_id=hedge_order['market_id'],
                    side='buy',
                    outcome=hedge_order['side'],
                    size=hedge_order['size'],
                    price=hedge_order['estimated_price']
                )

            return {
                'status': result.get('status', 'unknown'),
                'order_id': result.get('order_id', ''),
                'filled_size': result.get('filled_size', hedge_order['size']),
                'filled_price': result.get('avg_price', hedge_order['estimated_price']),
                'filled_cost': result.get('filled_size', hedge_order['size']) * result.get('avg_price', hedge_order['estimated_price']),
                **hedge_order
            }

        except Exception as e:
            logger.error(f"Order execution error: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                **hedge_order
            }

    def _calculate_pnl(self, position: Position) -> float:
        """PnL 계산"""

        # 간단한 PnL 계산
        # 실제로는 더 복잡한 로직 필요

        invested = position.size * (position.entry_price_a + position.entry_price_b)

        if position.current_price_a and position.current_price_b:
            current_value = position.size * (position.current_price_a + position.current_price_b)
            return current_value - invested
        else:
            return 0.0

    async def auto_hedge_on_threshold(
        self,
        position: Position,
        profit_threshold: float = 50.0,
        loss_threshold: float = -20.0
    ):
        """자동 헤지 (임계값 기반)"""

        pnl = self._calculate_pnl(position)

        if pnl >= profit_threshold:
            # 수익 목표 달성 -> 자동 헤지
            logger.info(f"Profit threshold reached: {pnl}. Auto-hedging...")
            hedge_plan = await self.calculate_hedge(position, hedge_percentage=100.0)
            result = await self.execute_hedge(position, hedge_plan)
            return result

        elif pnl <= loss_threshold:
            # 손실 한도 -> 자동 헤지 (손실 제한)
            logger.warning(f"Loss threshold reached: {pnl}. Auto-hedging...")
            hedge_plan = await self.calculate_hedge(position, hedge_percentage=50.0)  # 부분 헤지
            result = await self.execute_hedge(position, hedge_plan)
            return result

        return None

# ===========================
# 포지션 관리자 (Mock)
# ===========================

class PositionManager:
    """포지션 관리 (데모용)"""

    def __init__(self):
        self.positions: Dict[str, Position] = {}

    def add_position(self, position: Position):
        """포지션 추가"""
        self.positions[position.position_id] = position

    def get_position(self, position_id: str) -> Optional[Position]:
        """포지션 조회"""
        return self.positions.get(position_id)

    def get_all_positions(self) -> List[Position]:
        """전체 포지션"""
        return list(self.positions.values())

    async def update_position(self, position: Position):
        """포지션 업데이트"""
        self.positions[position.position_id] = position

# ===========================
# FastAPI 애플리케이션
# ===========================

# 글로벌 인스턴스
position_manager = PositionManager()
hedge_engine = None

# FastAPI 앱
app = FastAPI(
    title="Prediction Arbitrage Delta Hedge API",
    description="원클릭 델타헤지 시스템",
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
# API 엔드포인트
# ===========================

@app.get("/")
async def root():
    """API 정보"""
    return {
        "name": "Delta Hedge API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "positions": "/api/positions",
            "hedge_calculate": "/api/hedge/calculate/{position_id}",
            "hedge_execute": "/api/hedge/execute",
            "dashboard": "/api/dashboard"
        }
    }

@app.get("/api/positions", response_model=List[Position])
async def get_positions():
    """전체 포지션 조회"""
    return position_manager.get_all_positions()

@app.get("/api/positions/{position_id}", response_model=Position)
async def get_position(position_id: str):
    """특정 포지션 조회"""
    position = position_manager.get_position(position_id)
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    return position

@app.get("/api/hedge/calculate/{position_id}")
async def calculate_hedge(
    position_id: str,
    hedge_percentage: float = 100.0
):
    """헤지 계산"""
    position = position_manager.get_position(position_id)
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    if not hedge_engine:
        raise HTTPException(status_code=500, detail="Hedge engine not initialized")

    hedge_plan = await hedge_engine.calculate_hedge(position, hedge_percentage)

    return {
        "position_id": position_id,
        "hedge_plan": hedge_plan,
        "recommendation": hedge_plan['recommendation']
    }

@app.post("/api/hedge/execute", response_model=HedgeResult)
async def execute_hedge(
    request: HedgeRequest,
    background_tasks: BackgroundTasks
):
    """
    🔥 원클릭 델타헤지 실행

    이 엔드포인트는 대시보드의 "Hedge" 버튼과 연동됩니다.
    """
    position = position_manager.get_position(request.position_id)
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    if not hedge_engine:
        raise HTTPException(status_code=500, detail="Hedge engine not initialized")

    # 헤지 계획 생성
    hedge_plan = await hedge_engine.calculate_hedge(
        position,
        hedge_percentage=request.hedge_percentage or 100.0
    )

    # 헤지 실행
    result = await hedge_engine.execute_hedge(position, hedge_plan)

    # 백그라운드 알림
    # background_tasks.add_task(send_hedge_notification, result)

    return result

@app.get("/api/dashboard", response_model=DashboardData)
async def get_dashboard():
    """대시보드 데이터"""
    positions = position_manager.get_all_positions()

    total_pnl = sum(
        hedge_engine._calculate_pnl(p) if hedge_engine else 0.0
        for p in positions
    )

    return DashboardData(
        active_positions=len(positions),
        total_pnl=total_pnl,
        hedged_positions=sum(1 for p in positions if p.is_hedged),
        pending_hedges=0,
        opportunities=[],
        recent_trades=[],
        alerts=[]
    )

@app.post("/api/positions/create")
async def create_position(position: Position):
    """포지션 생성 (테스트용)"""
    position_manager.add_position(position)
    return {"status": "created", "position_id": position.position_id}

# ===========================
# 초기화 및 실행
# ===========================

@app.on_event("startup")
async def startup_event():
    """앱 시작 시 초기화"""
    global hedge_engine

    # Mock clients (실제로는 실제 클라이언트 사용)
    platform_clients = {
        'polymarket': None,  # PolymarketClient 인스턴스
        'kalshi': None,      # KalshiClient 인스턴스
        'manifold': None     # ManifoldClient 인스턴스
    }

    hedge_engine = DeltaHedgeEngine(platform_clients, position_manager)

    # 샘플 포지션 추가 (데모)
    sample_position = Position(
        position_id="pos_001",
        market_a_id="poly_btc_100k",
        market_b_id="kalshi_btc_100k",
        platform_a="polymarket",
        platform_b="kalshi",
        side_a="yes",
        side_b="no",
        size=1000.0,
        entry_price_a=0.65,
        entry_price_b=0.30,
        current_price_a=0.70,  # 가격 상승
        current_price_b=0.28,  # 가격 하락
        is_hedged=False,
        created_at=datetime.now()
    )

    position_manager.add_position(sample_position)

    logger.info("Delta Hedge API initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """앱 종료 시 정리"""
    logger.info("Delta Hedge API shutting down")

# ===========================
# 메인 실행
# ===========================

if __name__ == "__main__":
    # API 서버 실행
    uvicorn.run(
        "delta_hedge_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

    # 사용 예시:
    # curl http://localhost:8000/api/positions
    # curl http://localhost:8000/api/hedge/calculate/pos_001
    # curl -X POST http://localhost:8000/api/hedge/execute \
    #      -H "Content-Type: application/json" \
    #      -d '{"position_id": "pos_001", "hedge_type": "full"}'
