"""
Web3 Prediction Market Arbitrage Bot
실시간 예측시장 차익거래 봇
Supports: Polymarket, Kalshi, Manifold Markets
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal
import pandas as pd
import numpy as np
from web3 import Web3
from eth_account import Account
import ccxt
import time

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===========================
# 데이터 모델 정의
# ===========================

@dataclass
class Market:
    """예측시장 데이터 모델"""
    platform: str
    market_id: str
    question: str
    yes_price: float
    no_price: float
    volume: float
    liquidity: float
    end_date: datetime
    resolution_source: str
    last_update: datetime

@dataclass
class ArbitrageOpportunity:
    """차익거래 기회 데이터 모델"""
    market1: Market
    market2: Market
    side1: str  # 'yes' or 'no'
    side2: str  # 'yes' or 'no'
    profit_percentage: float
    required_capital: float
    expected_profit: float
    confidence_score: float
    risk_factors: List[str]

@dataclass
class TradingSignal:
    """트레이딩 시그널"""
    opportunity: ArbitrageOpportunity
    action: str  # 'execute', 'monitor', 'skip'
    reason: str
    timestamp: datetime

# ===========================
# API 클라이언트들
# ===========================

class PolymarketClient:
    """Polymarket API 클라이언트"""
    
    def __init__(self, private_key: str):
        self.base_url = "https://clob.polymarket.com"
        self.gamma_url = "https://gamma-api.polymarket.com"
        self.private_key = private_key
        self.account = Account.from_key(private_key)
        self.w3 = Web3(Web3.HTTPProvider('https://polygon-rpc.com'))
        self.session = None
        
    async def initialize(self):
        """비동기 세션 초기화"""
        self.session = aiohttp.ClientSession()
        
    async def get_markets(self, active_only: bool = True) -> List[Dict]:
        """활성 마켓 목록 조회"""
        try:
            params = {"closed": "false"} if active_only else {}
            async with self.session.get(
                f"{self.gamma_url}/markets",
                params=params
            ) as response:
                data = await response.json()
                return data
        except Exception as e:
            logger.error(f"Polymarket markets fetch error: {e}")
            return []
    
    async def get_market_orderbook(self, market_id: str) -> Dict:
        """특정 마켓의 오더북 조회"""
        try:
            async with self.session.get(
                f"{self.base_url}/book",
                params={"token_id": market_id}
            ) as response:
                return await response.json()
        except Exception as e:
            logger.error(f"Polymarket orderbook error: {e}")
            return {}
    
    async def get_market_price(self, market_id: str) -> Tuple[float, float]:
        """마켓 가격 조회 (YES, NO)"""
        orderbook = await self.get_market_orderbook(market_id)
        
        if not orderbook:
            return 0.0, 0.0
            
        # 최고 매수/매도 가격 추출
        best_bid_yes = float(orderbook.get('bids', [{}])[0].get('price', 0))
        best_ask_yes = float(orderbook.get('asks', [{}])[0].get('price', 0))
        
        yes_price = (best_bid_yes + best_ask_yes) / 2 if best_ask_yes else best_bid_yes
        no_price = 1.0 - yes_price if yes_price else 0.0
        
        return yes_price, no_price
    
    async def place_order(
        self,
        market_id: str,
        side: str,  # 'buy' or 'sell'
        outcome: str,  # 'yes' or 'no'
        size: float,
        price: float
    ) -> Dict:
        """주문 실행"""
        try:
            order_data = {
                "market": market_id,
                "side": side,
                "outcome": outcome,
                "size": size,
                "price": price,
                "timestamp": int(time.time())
            }
            
            # 서명 생성 (실제 구현 필요)
            signature = self._sign_order(order_data)
            order_data["signature"] = signature
            
            async with self.session.post(
                f"{self.base_url}/order",
                json=order_data
            ) as response:
                return await response.json()
        except Exception as e:
            logger.error(f"Polymarket order placement error: {e}")
            return {"error": str(e)}
    
    def _sign_order(self, order_data: Dict) -> str:
        """주문 서명 생성"""
        # EIP-712 서명 구현 필요
        message = json.dumps(order_data, sort_keys=True)
        message_hash = Web3.keccak(text=message)
        signature = self.account.signHash(message_hash)
        return signature.signature.hex()
    
    async def close(self):
        """세션 종료"""
        if self.session:
            await self.session.close()

class KalshiClient:
    """Kalshi API 클라이언트"""
    
    def __init__(self, email: str, password: str):
        self.base_url = "https://api.elections.kalshi.com/trade-api/v2"
        self.email = email
        self.password = password
        self.token = None
        self.session = None
        
    async def initialize(self):
        """세션 초기화 및 인증"""
        self.session = aiohttp.ClientSession()
        await self.authenticate()
        
    async def authenticate(self):
        """Kalshi 인증"""
        try:
            async with self.session.post(
                f"{self.base_url}/login",
                json={"email": self.email, "password": self.password}
            ) as response:
                data = await response.json()
                self.token = data.get("token")
                logger.info("Kalshi authentication successful")
        except Exception as e:
            logger.error(f"Kalshi authentication error: {e}")
    
    async def get_markets(self, status: str = "open") -> List[Dict]:
        """마켓 목록 조회"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            async with self.session.get(
                f"{self.base_url}/markets",
                headers=headers,
                params={"status": status}
            ) as response:
                data = await response.json()
                return data.get("markets", [])
        except Exception as e:
            logger.error(f"Kalshi markets fetch error: {e}")
            return []
    
    async def get_market_orderbook(self, ticker: str) -> Dict:
        """오더북 조회"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            async with self.session.get(
                f"{self.base_url}/markets/{ticker}/orderbook",
                headers=headers
            ) as response:
                return await response.json()
        except Exception as e:
            logger.error(f"Kalshi orderbook error: {e}")
            return {}
    
    async def place_order(
        self,
        ticker: str,
        side: str,
        contracts: int,
        price: int  # Kalshi는 센트 단위
    ) -> Dict:
        """주문 실행"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            order_data = {
                "ticker": ticker,
                "action": side,
                "count": contracts,
                "type": "limit",
                "yes_price": price if side == "buy" else None,
                "no_price": price if side == "sell" else None
            }
            
            async with self.session.post(
                f"{self.base_url}/orders",
                headers=headers,
                json=order_data
            ) as response:
                return await response.json()
        except Exception as e:
            logger.error(f"Kalshi order placement error: {e}")
            return {"error": str(e)}
    
    async def close(self):
        """세션 종료"""
        if self.session:
            await self.session.close()

class ManifoldClient:
    """Manifold Markets API 클라이언트"""
    
    def __init__(self, api_key: str):
        self.base_url = "https://api.manifold.markets/v0"
        self.api_key = api_key
        self.session = None
        
    async def initialize(self):
        """세션 초기화"""
        self.session = aiohttp.ClientSession()
        
    async def get_markets(self, limit: int = 100) -> List[Dict]:
        """마켓 목록 조회"""
        try:
            async with self.session.get(
                f"{self.base_url}/markets",
                params={"limit": limit}
            ) as response:
                return await response.json()
        except Exception as e:
            logger.error(f"Manifold markets fetch error: {e}")
            return []
    
    async def get_market_by_id(self, market_id: str) -> Dict:
        """특정 마켓 정보 조회"""
        try:
            async with self.session.get(
                f"{self.base_url}/market/{market_id}"
            ) as response:
                return await response.json()
        except Exception as e:
            logger.error(f"Manifold market fetch error: {e}")
            return {}
    
    async def place_bet(
        self,
        market_id: str,
        outcome: str,
        amount: float
    ) -> Dict:
        """베팅 실행"""
        try:
            headers = {"Authorization": f"Key {self.api_key}"}
            bet_data = {
                "contractId": market_id,
                "outcome": outcome,
                "amount": amount
            }
            
            async with self.session.post(
                f"{self.base_url}/bet",
                headers=headers,
                json=bet_data
            ) as response:
                return await response.json()
        except Exception as e:
            logger.error(f"Manifold bet placement error: {e}")
            return {"error": str(e)}
    
    async def close(self):
        """세션 종료"""
        if self.session:
            await self.session.close()

# ===========================
# 차익거래 엔진
# ===========================

class ArbitrageEngine:
    """차익거래 탐색 및 실행 엔진"""
    
    def __init__(
        self,
        polymarket_client: PolymarketClient,
        kalshi_client: KalshiClient,
        manifold_client: ManifoldClient,
        min_profit_percentage: float = 1.0,
        max_risk_score: float = 0.3
    ):
        self.polymarket = polymarket_client
        self.kalshi = kalshi_client
        self.manifold = manifold_client
        self.min_profit_percentage = min_profit_percentage
        self.max_risk_score = max_risk_score
        self.active_positions = []
        self.historical_opportunities = []
        
    async def scan_markets(self) -> List[Market]:
        """모든 플랫폼에서 마켓 스캔"""
        all_markets = []
        
        # Polymarket 마켓
        poly_markets = await self.polymarket.get_markets()
        for pm in poly_markets:
            yes_price, no_price = await self.polymarket.get_market_price(
                pm.get("conditionId", "")
            )
            
            market = Market(
                platform="polymarket",
                market_id=pm.get("conditionId", ""),
                question=pm.get("question", ""),
                yes_price=yes_price,
                no_price=no_price,
                volume=float(pm.get("volume", 0)),
                liquidity=float(pm.get("liquidity", 0)),
                end_date=datetime.fromisoformat(
                    pm.get("endDate", datetime.now().isoformat())
                ),
                resolution_source=pm.get("resolutionSource", "UMA"),
                last_update=datetime.now()
            )
            all_markets.append(market)
        
        # Kalshi 마켓
        kalshi_markets = await self.kalshi.get_markets()
        for km in kalshi_markets:
            orderbook = await self.kalshi.get_market_orderbook(
                km.get("ticker", "")
            )
            
            yes_price = float(orderbook.get("yes_bid", 0)) / 100
            no_price = float(orderbook.get("no_bid", 0)) / 100
            
            market = Market(
                platform="kalshi",
                market_id=km.get("ticker", ""),
                question=km.get("title", ""),
                yes_price=yes_price,
                no_price=no_price,
                volume=float(km.get("volume", 0)),
                liquidity=float(km.get("open_interest", 0)),
                end_date=datetime.fromisoformat(
                    km.get("close_time", datetime.now().isoformat())
                ),
                resolution_source=km.get("resolution_source", "Kalshi"),
                last_update=datetime.now()
            )
            all_markets.append(market)
        
        # Manifold 마켓
        manifold_markets = await self.manifold.get_markets()
        for mm in manifold_markets:
            market = Market(
                platform="manifold",
                market_id=mm.get("id", ""),
                question=mm.get("question", ""),
                yes_price=float(mm.get("probability", 0)),
                no_price=1.0 - float(mm.get("probability", 0)),
                volume=float(mm.get("volume", 0)),
                liquidity=float(mm.get("totalLiquidity", 0)),
                end_date=datetime.fromtimestamp(
                    mm.get("closeTime", time.time()) / 1000
                ),
                resolution_source="Manifold",
                last_update=datetime.now()
            )
            all_markets.append(market)
        
        return all_markets
    
    def find_similar_markets(
        self,
        markets: List[Market],
        similarity_threshold: float = 0.8
    ) -> List[Tuple[Market, Market]]:
        """유사한 마켓 쌍 찾기"""
        similar_pairs = []
        
        for i in range(len(markets)):
            for j in range(i + 1, len(markets)):
                if markets[i].platform != markets[j].platform:
                    # 질문 유사도 계산 (간단한 버전)
                    similarity = self._calculate_similarity(
                        markets[i].question,
                        markets[j].question
                    )
                    
                    if similarity >= similarity_threshold:
                        similar_pairs.append((markets[i], markets[j]))
        
        return similar_pairs
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """텍스트 유사도 계산 (간단한 버전)"""
        # 실제로는 더 정교한 NLP 기법 사용 필요
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def calculate_arbitrage_opportunity(
        self,
        market1: Market,
        market2: Market
    ) -> Optional[ArbitrageOpportunity]:
        """차익거래 기회 계산"""
        
        # 가격 차이 계산
        price_diff_yes = abs(market1.yes_price - market2.yes_price)
        price_diff_no = abs(market1.no_price - market2.no_price)
        
        # 차익거래 가능 여부 확인
        total_cost = 0
        expected_return = 0
        best_strategy = None
        
        # 전략 1: Market1에서 YES 구매, Market2에서 NO 구매
        if market1.yes_price + market2.no_price < 1.0:
            total_cost = market1.yes_price + market2.no_price
            expected_return = 1.0
            best_strategy = ("yes", "no")
        
        # 전략 2: Market1에서 NO 구매, Market2에서 YES 구매
        elif market1.no_price + market2.yes_price < 1.0:
            total_cost = market1.no_price + market2.yes_price
            expected_return = 1.0
            best_strategy = ("no", "yes")
        
        if best_strategy and total_cost > 0:
            profit_percentage = ((expected_return - total_cost) / total_cost) * 100
            
            if profit_percentage >= self.min_profit_percentage:
                # 위험 요소 평가
                risk_factors = self._assess_risk_factors(market1, market2)
                confidence_score = self._calculate_confidence_score(
                    market1, market2, risk_factors
                )
                
                return ArbitrageOpportunity(
                    market1=market1,
                    market2=market2,
                    side1=best_strategy[0],
                    side2=best_strategy[1],
                    profit_percentage=profit_percentage,
                    required_capital=total_cost * 1000,  # 예시: $1000 단위
                    expected_profit=profit_percentage * 10,  # 예시 계산
                    confidence_score=confidence_score,
                    risk_factors=risk_factors
                )
        
        return None
    
    def _assess_risk_factors(
        self,
        market1: Market,
        market2: Market
    ) -> List[str]:
        """위험 요소 평가"""
        risks = []
        
        # 해결 소스 차이
        if market1.resolution_source != market2.resolution_source:
            risks.append("Different resolution sources")
        
        # 유동성 확인
        if market1.liquidity < 10000 or market2.liquidity < 10000:
            risks.append("Low liquidity")
        
        # 종료 시간 차이
        time_diff = abs((market1.end_date - market2.end_date).days)
        if time_diff > 1:
            risks.append(f"End date difference: {time_diff} days")
        
        # 질문 문구 차이
        similarity = self._calculate_similarity(
            market1.question,
            market2.question
        )
        if similarity < 0.95:
            risks.append(f"Question similarity: {similarity:.2f}")
        
        return risks
    
    def _calculate_confidence_score(
        self,
        market1: Market,
        market2: Market,
        risk_factors: List[str]
    ) -> float:
        """신뢰도 점수 계산"""
        score = 1.0
        
        # 위험 요소당 감점
        score -= len(risk_factors) * 0.1
        
        # 유동성 기반 조정
        liquidity_score = min(
            market1.liquidity / 100000,
            market2.liquidity / 100000,
            1.0
        )
        score *= liquidity_score
        
        # 거래량 기반 조정
        volume_score = min(
            market1.volume / 1000000,
            market2.volume / 1000000,
            1.0
        )
        score *= volume_score
        
        return max(0.0, min(1.0, score))
    
    async def execute_arbitrage(
        self,
        opportunity: ArbitrageOpportunity
    ) -> Dict:
        """차익거래 실행"""
        results = {
            "status": "pending",
            "trades": [],
            "error": None
        }
        
        try:
            # Market1 거래 실행
            if opportunity.market1.platform == "polymarket":
                trade1 = await self.polymarket.place_order(
                    market_id=opportunity.market1.market_id,
                    side="buy",
                    outcome=opportunity.side1,
                    size=opportunity.required_capital / 2,
                    price=opportunity.market1.yes_price if opportunity.side1 == "yes" else opportunity.market1.no_price
                )
            elif opportunity.market1.platform == "kalshi":
                trade1 = await self.kalshi.place_order(
                    ticker=opportunity.market1.market_id,
                    side="buy",
                    contracts=int(opportunity.required_capital / 2),
                    price=int((opportunity.market1.yes_price if opportunity.side1 == "yes" else opportunity.market1.no_price) * 100)
                )
            else:  # manifold
                trade1 = await self.manifold.place_bet(
                    market_id=opportunity.market1.market_id,
                    outcome=opportunity.side1.upper(),
                    amount=opportunity.required_capital / 2
                )
            
            results["trades"].append(trade1)
            
            # Market2 거래 실행
            if opportunity.market2.platform == "polymarket":
                trade2 = await self.polymarket.place_order(
                    market_id=opportunity.market2.market_id,
                    side="buy",
                    outcome=opportunity.side2,
                    size=opportunity.required_capital / 2,
                    price=opportunity.market2.yes_price if opportunity.side2 == "yes" else opportunity.market2.no_price
                )
            elif opportunity.market2.platform == "kalshi":
                trade2 = await self.kalshi.place_order(
                    ticker=opportunity.market2.market_id,
                    side="buy",
                    contracts=int(opportunity.required_capital / 2),
                    price=int((opportunity.market2.yes_price if opportunity.side2 == "yes" else opportunity.market2.no_price) * 100)
                )
            else:  # manifold
                trade2 = await self.manifold.place_bet(
                    market_id=opportunity.market2.market_id,
                    outcome=opportunity.side2.upper(),
                    amount=opportunity.required_capital / 2
                )
            
            results["trades"].append(trade2)
            results["status"] = "completed"
            
            # 포지션 기록
            self.active_positions.append({
                "opportunity": opportunity,
                "execution_time": datetime.now(),
                "trades": results["trades"]
            })
            
        except Exception as e:
            results["status"] = "failed"
            results["error"] = str(e)
            logger.error(f"Arbitrage execution failed: {e}")
        
        return results
    
    async def monitor_and_execute(self):
        """지속적인 모니터링 및 실행"""
        logger.info("Starting arbitrage monitoring...")
        
        while True:
            try:
                # 마켓 스캔
                markets = await self.scan_markets()
                logger.info(f"Scanned {len(markets)} markets")
                
                # 유사 마켓 찾기
                similar_pairs = self.find_similar_markets(markets)
                logger.info(f"Found {len(similar_pairs)} similar market pairs")
                
                # 차익거래 기회 탐색
                opportunities = []
                for market1, market2 in similar_pairs:
                    opportunity = self.calculate_arbitrage_opportunity(
                        market1, market2
                    )
                    if opportunity:
                        opportunities.append(opportunity)
                
                logger.info(f"Found {len(opportunities)} arbitrage opportunities")
                
                # 기회 정렬 (수익률 순)
                opportunities.sort(
                    key=lambda x: x.profit_percentage,
                    reverse=True
                )
                
                # 최상의 기회 실행
                for opportunity in opportunities:
                    if opportunity.confidence_score >= (1.0 - self.max_risk_score):
                        logger.info(
                            f"Executing arbitrage: {opportunity.profit_percentage:.2f}% profit"
                        )
                        
                        result = await self.execute_arbitrage(opportunity)
                        
                        if result["status"] == "completed":
                            logger.info("Arbitrage executed successfully")
                        else:
                            logger.warning(f"Arbitrage failed: {result['error']}")
                
                # 대기
                await asyncio.sleep(60)  # 1분마다 스캔
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(60)

# ===========================
# 리스크 관리
# ===========================

class RiskManager:
    """리스크 관리 시스템"""
    
    def __init__(
        self,
        max_position_size: float = 10000,
        max_total_exposure: float = 50000,
        max_single_market_exposure: float = 5000,
        stop_loss_percentage: float = 5.0
    ):
        self.max_position_size = max_position_size
        self.max_total_exposure = max_total_exposure
        self.max_single_market_exposure = max_single_market_exposure
        self.stop_loss_percentage = stop_loss_percentage
        self.current_exposure = {}
        self.total_exposure = 0
        
    def can_take_position(
        self,
        opportunity: ArbitrageOpportunity
    ) -> Tuple[bool, str]:
        """포지션 진입 가능 여부 확인"""
        
        # 총 노출도 확인
        if self.total_exposure + opportunity.required_capital > self.max_total_exposure:
            return False, "Exceeds total exposure limit"
        
        # 단일 포지션 크기 확인
        if opportunity.required_capital > self.max_position_size:
            return False, "Position size too large"
        
        # 마켓별 노출도 확인
        market_exposure = self.current_exposure.get(
            opportunity.market1.market_id, 0
        ) + self.current_exposure.get(
            opportunity.market2.market_id, 0
        )
        
        if market_exposure + opportunity.required_capital > self.max_single_market_exposure:
            return False, "Exceeds single market exposure limit"
        
        # 리스크 점수 확인
        if opportunity.confidence_score < 0.7:
            return False, "Confidence score too low"
        
        # 위험 요소 확인
        if len(opportunity.risk_factors) > 3:
            return False, "Too many risk factors"
        
        return True, "Position approved"
    
    def update_exposure(
        self,
        market_id: str,
        amount: float,
        operation: str = "add"
    ):
        """노출도 업데이트"""
        if operation == "add":
            self.current_exposure[market_id] = self.current_exposure.get(
                market_id, 0
            ) + amount
            self.total_exposure += amount
        elif operation == "remove":
            self.current_exposure[market_id] = max(
                0,
                self.current_exposure.get(market_id, 0) - amount
            )
            self.total_exposure = max(0, self.total_exposure - amount)
    
    def calculate_var(
        self,
        positions: List[Dict],
        confidence_level: float = 0.95
    ) -> float:
        """Value at Risk 계산"""
        if not positions:
            return 0.0
        
        # 포지션별 수익률 시뮬레이션
        returns = []
        for position in positions:
            opportunity = position["opportunity"]
            # 간단한 시뮬레이션 (실제로는 더 정교한 모델 필요)
            expected_return = opportunity.expected_profit
            std_dev = expected_return * 0.3  # 예시: 30% 표준편차
            
            # 정규분포 가정
            simulated_returns = np.random.normal(
                expected_return,
                std_dev,
                1000
            )
            returns.extend(simulated_returns)
        
        # VaR 계산
        var = np.percentile(returns, (1 - confidence_level) * 100)
        return abs(var)

# ===========================
# 대시보드 및 모니터링
# ===========================

class Dashboard:
    """실시간 대시보드"""
    
    def __init__(self, engine: ArbitrageEngine, risk_manager: RiskManager):
        self.engine = engine
        self.risk_manager = risk_manager
        self.start_time = datetime.now()
        
    def generate_report(self) -> Dict:
        """현재 상태 리포트 생성"""
        uptime = datetime.now() - self.start_time
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "uptime": str(uptime),
            "active_positions": len(self.engine.active_positions),
            "total_exposure": self.risk_manager.total_exposure,
            "opportunities_found": len(self.engine.historical_opportunities),
            "current_positions": [],
            "performance_metrics": {}
        }
        
        # 포지션 상세 정보
        for position in self.engine.active_positions:
            pos_info = {
                "markets": [
                    position["opportunity"].market1.platform,
                    position["opportunity"].market2.platform
                ],
                "profit_percentage": position["opportunity"].profit_percentage,
                "confidence": position["opportunity"].confidence_score,
                "execution_time": position["execution_time"].isoformat()
            }
            report["current_positions"].append(pos_info)
        
        # 성과 지표 계산
        if self.engine.historical_opportunities:
            profits = [
                opp.profit_percentage 
                for opp in self.engine.historical_opportunities
            ]
            report["performance_metrics"] = {
                "average_profit": np.mean(profits),
                "max_profit": np.max(profits),
                "min_profit": np.min(profits),
                "total_opportunities": len(profits)
            }
        
        return report
    
    def print_status(self):
        """콘솔에 상태 출력"""
        report = self.generate_report()
        
        print("\n" + "="*60)
        print("🤖 PREDICTION MARKET ARBITRAGE BOT STATUS")
        print("="*60)
        print(f"⏰ Time: {report['timestamp']}")
        print(f"⏱️  Uptime: {report['uptime']}")
        print(f"📊 Active Positions: {report['active_positions']}")
        print(f"💰 Total Exposure: ${report['total_exposure']:,.2f}")
        print(f"🎯 Opportunities Found: {report['opportunities_found']}")
        
        if report['performance_metrics']:
            print("\n📈 Performance Metrics:")
            for key, value in report['performance_metrics'].items():
                print(f"  - {key.replace('_', ' ').title()}: {value:.2f}")
        
        if report['current_positions']:
            print("\n📝 Current Positions:")
            for i, pos in enumerate(report['current_positions'], 1):
                print(f"  {i}. {pos['markets'][0]} ↔️ {pos['markets'][1]}")
                print(f"     Profit: {pos['profit_percentage']:.2f}%")
                print(f"     Confidence: {pos['confidence']:.2f}")
        
        print("="*60)

# ===========================
# 메인 실행 함수
# ===========================

async def main():
    """메인 실행 함수"""
    
    # 환경 변수에서 설정 로드 (실제 사용시 .env 파일 활용)
    config = {
        "polymarket_private_key": "YOUR_PRIVATE_KEY",
        "kalshi_email": "YOUR_EMAIL",
        "kalshi_password": "YOUR_PASSWORD",
        "manifold_api_key": "YOUR_API_KEY",
        "min_profit_percentage": 1.0,
        "max_risk_score": 0.3
    }
    
    # 클라이언트 초기화
    polymarket_client = PolymarketClient(config["polymarket_private_key"])
    kalshi_client = KalshiClient(config["kalshi_email"], config["kalshi_password"])
    manifold_client = ManifoldClient(config["manifold_api_key"])
    
    # 세션 초기화
    await polymarket_client.initialize()
    await kalshi_client.initialize()
    await manifold_client.initialize()
    
    # 차익거래 엔진 생성
    engine = ArbitrageEngine(
        polymarket_client=polymarket_client,
        kalshi_client=kalshi_client,
        manifold_client=manifold_client,
        min_profit_percentage=config["min_profit_percentage"],
        max_risk_score=config["max_risk_score"]
    )
    
    # 리스크 매니저 생성
    risk_manager = RiskManager()
    
    # 대시보드 생성
    dashboard = Dashboard(engine, risk_manager)
    
    # 상태 출력 태스크
    async def print_status_periodically():
        while True:
            dashboard.print_status()
            await asyncio.sleep(300)  # 5분마다 상태 출력
    
    # 비동기 태스크 실행
    try:
        await asyncio.gather(
            engine.monitor_and_execute(),
            print_status_periodically()
        )
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    finally:
        # 클린업
        await polymarket_client.close()
        await kalshi_client.close()
        await manifold_client.close()

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║   WEB3 PREDICTION MARKET ARBITRAGE BOT              ║
    ║   Supporting: Polymarket, Kalshi, Manifold          ║
    ║   Version: 1.0.0                                     ║
    ╚══════════════════════════════════════════════════════╝
    """)
    
    # 이벤트 루프 실행
    asyncio.run(main())
