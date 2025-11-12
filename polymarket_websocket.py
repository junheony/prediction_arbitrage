"""
Polymarket Gamma + CLOB WebSocket Connector
실시간 시세/호가/체결 데이터 스트리밍
"""

import asyncio
import websockets
import json
import logging
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from collections import defaultdict
import aiohttp

logger = logging.getLogger(__name__)

# ===========================
# 데이터 모델
# ===========================

@dataclass
class OrderbookUpdate:
    """오더북 업데이트"""
    token_id: str
    timestamp: datetime
    bids: List[Dict[str, Any]]  # [{"price": "0.65", "size": "1000"}, ...]
    asks: List[Dict[str, Any]]
    market: str
    asset_id: str

@dataclass
class TradeUpdate:
    """체결 데이터"""
    token_id: str
    timestamp: datetime
    price: Decimal
    size: Decimal
    side: str  # 'buy' or 'sell'
    trade_id: str
    maker_address: str
    taker_address: str

@dataclass
class MarketUpdate:
    """마켓 데이터 업데이트"""
    condition_id: str
    question: str
    yes_price: Decimal
    no_price: Decimal
    volume_24h: Decimal
    liquidity: Decimal
    last_trade_price: Decimal
    timestamp: datetime

@dataclass
class PriceLevel:
    """가격 레벨"""
    price: Decimal
    size: Decimal

# ===========================
# Polymarket WebSocket 클라이언트
# ===========================

class PolymarketWebSocketClient:
    """
    Polymarket CLOB WebSocket 클라이언트

    Endpoints:
    - wss://ws-subscriptions-clob.polymarket.com/ws/market/{token_id}
    - wss://ws-subscriptions-clob.polymarket.com/ws/markets
    """

    def __init__(
        self,
        on_orderbook: Optional[Callable] = None,
        on_trade: Optional[Callable] = None,
        on_market_update: Optional[Callable] = None
    ):
        self.clob_ws_base = "wss://ws-subscriptions-clob.polymarket.com"
        self.gamma_api_base = "https://gamma-api.polymarket.com"

        # 콜백 함수
        self.on_orderbook = on_orderbook
        self.on_trade = on_trade
        self.on_market_update = on_market_update

        # WebSocket 연결
        self.connections = {}
        self.subscribed_markets = set()

        # 데이터 캐시
        self.orderbooks = {}  # token_id -> OrderbookUpdate
        self.latest_trades = defaultdict(list)  # token_id -> List[TradeUpdate]
        self.market_data = {}  # condition_id -> MarketUpdate

        # HTTP 세션
        self.http_session = None

        # 상태 관리
        self.running = False
        self.reconnect_delay = 5  # 재연결 지연 (초)

    async def initialize(self):
        """클라이언트 초기화"""
        self.http_session = aiohttp.ClientSession()
        logger.info("Polymarket WebSocket client initialized")

    async def connect_market_stream(self, token_id: str):
        """
        특정 마켓 WebSocket 연결

        Args:
            token_id: 토큰 ID (예: "0x123...")
        """
        if token_id in self.connections:
            logger.warning(f"Already connected to {token_id}")
            return

        ws_url = f"{self.clob_ws_base}/ws/market/{token_id}"

        try:
            logger.info(f"Connecting to {ws_url}")
            websocket = await websockets.connect(ws_url)
            self.connections[token_id] = websocket
            self.subscribed_markets.add(token_id)

            # 리스닝 태스크 시작
            asyncio.create_task(self._listen_market_stream(token_id, websocket))

            logger.info(f"Successfully connected to market {token_id}")

        except Exception as e:
            logger.error(f"Failed to connect to {token_id}: {e}")

    async def connect_all_markets_stream(self):
        """전체 마켓 스트림 연결"""
        ws_url = f"{self.clob_ws_base}/ws/markets"

        try:
            logger.info(f"Connecting to all markets stream: {ws_url}")
            websocket = await websockets.connect(ws_url)
            self.connections['__all__'] = websocket

            # 리스닝 태스크 시작
            asyncio.create_task(self._listen_all_markets_stream(websocket))

            logger.info("Successfully connected to all markets stream")

        except Exception as e:
            logger.error(f"Failed to connect to all markets stream: {e}")

    async def _listen_market_stream(self, token_id: str, websocket):
        """개별 마켓 스트림 리스닝"""
        try:
            while self.running:
                message = await websocket.recv()
                data = json.loads(message)

                # 메시지 타입 파싱
                msg_type = data.get('type')

                if msg_type == 'book':
                    await self._handle_orderbook_update(token_id, data)
                elif msg_type == 'trade':
                    await self._handle_trade_update(token_id, data)
                elif msg_type == 'last_trade_price':
                    await self._handle_price_update(token_id, data)
                else:
                    logger.debug(f"Unknown message type: {msg_type}")

        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"Connection closed for {token_id}, reconnecting...")
            await self._reconnect_market(token_id)
        except Exception as e:
            logger.error(f"Error in market stream {token_id}: {e}")

    async def _listen_all_markets_stream(self, websocket):
        """전체 마켓 스트림 리스닝"""
        try:
            while self.running:
                message = await websocket.recv()
                data = json.loads(message)

                # 전체 마켓 데이터 처리
                if 'markets' in data:
                    for market_data in data['markets']:
                        await self._handle_market_snapshot(market_data)

        except websockets.exceptions.ConnectionClosed:
            logger.warning("All markets connection closed, reconnecting...")
            await self._reconnect_all_markets()
        except Exception as e:
            logger.error(f"Error in all markets stream: {e}")

    async def _handle_orderbook_update(self, token_id: str, data: Dict):
        """오더북 업데이트 처리"""
        try:
            # 데이터 파싱
            bids = [
                {"price": Decimal(level[0]), "size": Decimal(level[1])}
                for level in data.get('bids', [])
            ]
            asks = [
                {"price": Decimal(level[0]), "size": Decimal(level[1])}
                for level in data.get('asks', [])
            ]

            update = OrderbookUpdate(
                token_id=token_id,
                timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat())),
                bids=bids,
                asks=asks,
                market=data.get('market', ''),
                asset_id=data.get('asset_id', token_id)
            )

            # 캐시 업데이트
            self.orderbooks[token_id] = update

            # 콜백 실행
            if self.on_orderbook:
                await self.on_orderbook(update)

            logger.debug(
                f"Orderbook update: {token_id} - "
                f"Best bid: {bids[0]['price'] if bids else 'N/A'}, "
                f"Best ask: {asks[0]['price'] if asks else 'N/A'}"
            )

        except Exception as e:
            logger.error(f"Error handling orderbook update: {e}")

    async def _handle_trade_update(self, token_id: str, data: Dict):
        """체결 데이터 처리"""
        try:
            trade = TradeUpdate(
                token_id=token_id,
                timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat())),
                price=Decimal(data.get('price', '0')),
                size=Decimal(data.get('size', '0')),
                side=data.get('side', 'buy'),
                trade_id=data.get('id', ''),
                maker_address=data.get('maker', ''),
                taker_address=data.get('taker', '')
            )

            # 캐시 업데이트 (최근 100개만 유지)
            self.latest_trades[token_id].append(trade)
            if len(self.latest_trades[token_id]) > 100:
                self.latest_trades[token_id].pop(0)

            # 콜백 실행
            if self.on_trade:
                await self.on_trade(trade)

            logger.debug(
                f"Trade: {token_id} - "
                f"Price: {trade.price}, Size: {trade.size}, Side: {trade.side}"
            )

        except Exception as e:
            logger.error(f"Error handling trade update: {e}")

    async def _handle_price_update(self, token_id: str, data: Dict):
        """가격 업데이트 처리"""
        try:
            price = Decimal(data.get('price', '0'))

            # 간단한 가격 업데이트만 로깅
            logger.debug(f"Price update: {token_id} - {price}")

        except Exception as e:
            logger.error(f"Error handling price update: {e}")

    async def _handle_market_snapshot(self, data: Dict):
        """마켓 스냅샷 처리"""
        try:
            market_update = MarketUpdate(
                condition_id=data.get('condition_id', ''),
                question=data.get('question', ''),
                yes_price=Decimal(data.get('yes_price', '0')),
                no_price=Decimal(data.get('no_price', '0')),
                volume_24h=Decimal(data.get('volume', '0')),
                liquidity=Decimal(data.get('liquidity', '0')),
                last_trade_price=Decimal(data.get('last_trade_price', '0')),
                timestamp=datetime.now()
            )

            # 캐시 업데이트
            self.market_data[market_update.condition_id] = market_update

            # 콜백 실행
            if self.on_market_update:
                await self.on_market_update(market_update)

        except Exception as e:
            logger.error(f"Error handling market snapshot: {e}")

    async def _reconnect_market(self, token_id: str):
        """마켓 재연결"""
        logger.info(f"Reconnecting to {token_id} in {self.reconnect_delay}s...")
        await asyncio.sleep(self.reconnect_delay)

        # 기존 연결 정리
        if token_id in self.connections:
            try:
                await self.connections[token_id].close()
            except:
                pass
            del self.connections[token_id]

        # 재연결
        await self.connect_market_stream(token_id)

    async def _reconnect_all_markets(self):
        """전체 마켓 재연결"""
        logger.info(f"Reconnecting to all markets in {self.reconnect_delay}s...")
        await asyncio.sleep(self.reconnect_delay)

        # 기존 연결 정리
        if '__all__' in self.connections:
            try:
                await self.connections['__all__'].close()
            except:
                pass
            del self.connections['__all__']

        # 재연결
        await self.connect_all_markets_stream()

    async def get_active_markets(self) -> List[Dict]:
        """
        Gamma API로 활성 마켓 목록 조회

        Returns:
            List of market dictionaries
        """
        try:
            url = f"{self.gamma_api_base}/markets"
            params = {"closed": "false", "active": "true"}

            async with self.http_session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Fetched {len(data)} active markets")
                    return data
                else:
                    logger.error(f"Failed to fetch markets: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching active markets: {e}")
            return []

    async def subscribe_to_top_markets(self, limit: int = 10):
        """
        거래량 상위 마켓에 자동 구독

        Args:
            limit: 구독할 마켓 개수
        """
        markets = await self.get_active_markets()

        # 거래량 기준 정렬
        sorted_markets = sorted(
            markets,
            key=lambda x: float(x.get('volume', 0)),
            reverse=True
        )[:limit]

        logger.info(f"Subscribing to top {limit} markets by volume")

        for market in sorted_markets:
            tokens = market.get('tokens', [])
            for token in tokens:
                token_id = token.get('token_id')
                if token_id:
                    await self.connect_market_stream(token_id)
                    await asyncio.sleep(0.5)  # Rate limiting

    def get_orderbook(self, token_id: str) -> Optional[OrderbookUpdate]:
        """캐시된 오더북 조회"""
        return self.orderbooks.get(token_id)

    def get_best_prices(self, token_id: str) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        """최고 매수/매도 가격 조회"""
        orderbook = self.get_orderbook(token_id)
        if not orderbook:
            return None, None

        best_bid = orderbook.bids[0]['price'] if orderbook.bids else None
        best_ask = orderbook.asks[0]['price'] if orderbook.asks else None

        return best_bid, best_ask

    def get_mid_price(self, token_id: str) -> Optional[Decimal]:
        """중간 가격 조회"""
        best_bid, best_ask = self.get_best_prices(token_id)

        if best_bid and best_ask:
            return (best_bid + best_ask) / 2
        elif best_bid:
            return best_bid
        elif best_ask:
            return best_ask
        else:
            return None

    def get_spread(self, token_id: str) -> Optional[Decimal]:
        """스프레드 조회"""
        best_bid, best_ask = self.get_best_prices(token_id)

        if best_bid and best_ask:
            return best_ask - best_bid
        else:
            return None

    def get_recent_trades(self, token_id: str, limit: int = 10) -> List[TradeUpdate]:
        """최근 체결 데이터 조회"""
        trades = self.latest_trades.get(token_id, [])
        return trades[-limit:] if trades else []

    async def start(self):
        """WebSocket 클라이언트 시작"""
        self.running = True
        logger.info("Polymarket WebSocket client started")

    async def stop(self):
        """WebSocket 클라이언트 종료"""
        self.running = False

        # 모든 연결 종료
        for token_id, ws in self.connections.items():
            try:
                await ws.close()
                logger.info(f"Closed connection: {token_id}")
            except Exception as e:
                logger.error(f"Error closing {token_id}: {e}")

        self.connections.clear()
        self.subscribed_markets.clear()

        # HTTP 세션 종료
        if self.http_session:
            await self.http_session.close()

        logger.info("Polymarket WebSocket client stopped")

    def get_status(self) -> Dict:
        """연결 상태 조회"""
        return {
            'running': self.running,
            'connected_markets': len(self.connections),
            'subscribed_markets': list(self.subscribed_markets),
            'cached_orderbooks': len(self.orderbooks),
            'total_trades_cached': sum(len(trades) for trades in self.latest_trades.values())
        }

# ===========================
# 사용 예시
# ===========================

async def example_callbacks():
    """콜백 예시"""

    async def on_orderbook_update(update: OrderbookUpdate):
        """오더북 업데이트 콜백"""
        best_bid = update.bids[0]['price'] if update.bids else 'N/A'
        best_ask = update.asks[0]['price'] if update.asks else 'N/A'
        spread = float(update.asks[0]['price'] - update.bids[0]['price']) if update.bids and update.asks else 0

        print(f"📊 Orderbook Update - {update.token_id[:8]}...")
        print(f"   Best Bid: {best_bid} | Best Ask: {best_ask} | Spread: {spread:.4f}")

    async def on_trade(trade: TradeUpdate):
        """체결 콜백"""
        print(f"💰 Trade - {trade.token_id[:8]}... | "
              f"Price: {trade.price} | Size: {trade.size} | Side: {trade.side}")

    async def on_market_update(market: MarketUpdate):
        """마켓 업데이트 콜백"""
        print(f"📈 Market - {market.question[:50]}... | "
              f"Yes: {market.yes_price} | No: {market.no_price}")

    # 클라이언트 생성
    client = PolymarketWebSocketClient(
        on_orderbook=on_orderbook_update,
        on_trade=on_trade,
        on_market_update=on_market_update
    )

    # 초기화
    await client.initialize()
    await client.start()

    # 상위 마켓 구독
    await client.subscribe_to_top_markets(limit=5)

    # 또는 특정 토큰 구독
    # await client.connect_market_stream("0x1234...")

    # 일정 시간 실행
    try:
        print("\n🚀 WebSocket client running... (Press Ctrl+C to stop)\n")
        await asyncio.sleep(300)  # 5분간 실행
    except KeyboardInterrupt:
        print("\n\n⏸️  Stopping...")

    # 종료
    await client.stop()

    # 상태 출력
    print("\n📊 Final Status:")
    status = client.get_status()
    print(json.dumps(status, indent=2))

async def example_simple_usage():
    """간단한 사용 예시"""

    # 콜백 없이 사용
    client = PolymarketWebSocketClient()
    await client.initialize()
    await client.start()

    # 특정 토큰 구독
    token_id = "21742633143463906290569050155826241533067272736897614950488156847949938836455"
    await client.connect_market_stream(token_id)

    # 데이터 수집
    await asyncio.sleep(10)

    # 데이터 조회
    orderbook = client.get_orderbook(token_id)
    if orderbook:
        print(f"Best Bid: {orderbook.bids[0] if orderbook.bids else 'N/A'}")
        print(f"Best Ask: {orderbook.asks[0] if orderbook.asks else 'N/A'}")

    mid_price = client.get_mid_price(token_id)
    print(f"Mid Price: {mid_price}")

    spread = client.get_spread(token_id)
    print(f"Spread: {spread}")

    recent_trades = client.get_recent_trades(token_id, limit=5)
    print(f"Recent Trades: {len(recent_trades)}")

    await client.stop()

if __name__ == "__main__":
    # 콜백 예시 실행
    asyncio.run(example_callbacks())

    # 또는 간단한 예시
    # asyncio.run(example_simple_usage())
