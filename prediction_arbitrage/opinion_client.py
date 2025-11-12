"""
Opinion.trade REST + WebSocket Client
Real-time market data and trading for Opinion prediction markets
Based on official Opinion.trade API documentation
"""

import asyncio
import aiohttp
import logging
from typing import Optional, Callable, Dict, List, Any
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

# ===========================
# Data Models
# ===========================

@dataclass
class OpinionMarket:
    """Opinion market structure"""
    market_id: str
    title: str
    description: str
    category: str
    close_time: datetime
    token_yes_id: str
    token_no_id: str
    yes_price: Optional[Decimal] = None
    no_price: Optional[Decimal] = None
    volume: Decimal = Decimal('0')
    liquidity: Decimal = Decimal('0')
    status: str = "active"

    @property
    def best_yes_price(self) -> Optional[Decimal]:
        """Best YES price"""
        return self.yes_price

    @property
    def best_no_price(self) -> Optional[Decimal]:
        """Best NO price"""
        return self.no_price


@dataclass
class OpinionOrderbook:
    """Opinion orderbook structure"""
    token_id: str
    market_id: str
    bids: List[Dict[str, Any]]  # [{'price': decimal, 'size': decimal}]
    asks: List[Dict[str, Any]]
    timestamp: datetime

    def get_best_bid(self) -> Optional[Decimal]:
        """Get best bid price"""
        if self.bids:
            return Decimal(str(self.bids[0]['price']))
        return None

    def get_best_ask(self) -> Optional[Decimal]:
        """Get best ask price"""
        if self.asks:
            return Decimal(str(self.asks[0]['price']))
        return None


@dataclass
class OpinionTrade:
    """Opinion trade structure"""
    trade_id: str
    market_id: str
    token_id: str
    side: str  # 'BUY' or 'SELL'
    price: Decimal
    size: Decimal
    timestamp: datetime


# ===========================
# Opinion REST Client
# ===========================

class OpinionRestClient:
    """Opinion.trade REST API client"""

    BASE_URL = "https://api.opinion.trade/v1"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Opinion REST client

        Args:
            api_key: Optional API key for authenticated endpoints
        """
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        """Initialize session"""
        headers = {}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        self.session = aiohttp.ClientSession(headers=headers)
        logger.info("✅ Opinion REST client initialized")

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make API request"""
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"

        try:
            async with self.session.request(method, url, **kwargs) as resp:
                if resp.status == 200:
                    data = await resp.json()

                    # Opinion API returns {errno: 0, errmsg: '', result: {...}}
                    if data.get('errno') == 0:
                        return data.get('result', {})
                    else:
                        error_msg = data.get('errmsg', 'Unknown error')
                        logger.error(f"❌ Opinion API error: {error_msg}")
                        raise Exception(f"Opinion API error: {error_msg}")
                else:
                    error = await resp.text()
                    logger.error(f"❌ Opinion HTTP error {resp.status}: {error}")
                    raise Exception(f"Opinion HTTP error: {error}")

        except Exception as e:
            logger.error(f"❌ Opinion request error: {e}")
            raise

    async def get_markets(
        self,
        topic_type: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
        status: Optional[str] = None
    ) -> List[OpinionMarket]:
        """
        Get list of markets

        Args:
            topic_type: Filter by category (e.g., 'crypto', 'politics')
            page: Page number
            limit: Results per page
            status: Market status filter
        """
        try:
            params = {'page': page, 'limit': limit}
            if topic_type:
                params['topic_type'] = topic_type
            if status:
                params['status'] = status

            result = await self._request('GET', '/markets', params=params)

            markets = []
            for m in result.get('list', []):
                market = OpinionMarket(
                    market_id=m['market_id'],
                    title=m['title'],
                    description=m.get('description', ''),
                    category=m.get('category', ''),
                    close_time=datetime.fromtimestamp(m['end_at']) if m.get('end_at') else None,
                    token_yes_id=m.get('token_yes_id', ''),
                    token_no_id=m.get('token_no_id', ''),
                    yes_price=Decimal(str(m.get('yes_price', 0))) if m.get('yes_price') else None,
                    no_price=Decimal(str(m.get('no_price', 0))) if m.get('no_price') else None,
                    volume=Decimal(str(m.get('volume', 0))),
                    liquidity=Decimal(str(m.get('liquidity', 0))),
                    status=m.get('status', 'active')
                )
                markets.append(market)

            logger.info(f"📊 Retrieved {len(markets)} Opinion markets")
            return markets

        except Exception as e:
            logger.error(f"❌ Error fetching Opinion markets: {e}")
            return []

    async def get_market(self, market_id: str, use_cache: bool = True) -> Optional[OpinionMarket]:
        """Get single market details"""
        try:
            result = await self._request(
                'GET',
                f'/markets/{market_id}',
                params={'use_cache': use_cache}
            )

            m = result.get('data', {})
            if not m:
                return None

            return OpinionMarket(
                market_id=m['market_id'],
                title=m['title'],
                description=m.get('description', ''),
                category=m.get('category', ''),
                close_time=datetime.fromtimestamp(m['end_at']) if m.get('end_at') else None,
                token_yes_id=m.get('token_yes_id', ''),
                token_no_id=m.get('token_no_id', ''),
                yes_price=Decimal(str(m.get('yes_price', 0))) if m.get('yes_price') else None,
                no_price=Decimal(str(m.get('no_price', 0))) if m.get('no_price') else None,
                volume=Decimal(str(m.get('volume', 0))),
                liquidity=Decimal(str(m.get('liquidity', 0))),
                status=m.get('status', 'active')
            )

        except Exception as e:
            logger.error(f"❌ Error fetching Opinion market {market_id}: {e}")
            return None

    async def get_orderbook(self, token_id: str) -> Optional[OpinionOrderbook]:
        """Get orderbook for a token"""
        try:
            result = await self._request('GET', f'/orderbook/{token_id}')

            ob = result.get('data', {})
            if not ob:
                return None

            return OpinionOrderbook(
                token_id=token_id,
                market_id=ob.get('market_id', ''),
                bids=ob.get('bids', []),
                asks=ob.get('asks', []),
                timestamp=datetime.now()
            )

        except Exception as e:
            logger.error(f"❌ Error fetching Opinion orderbook {token_id}: {e}")
            return None

    async def get_latest_price(self, token_id: str) -> Optional[Decimal]:
        """Get latest price for a token"""
        try:
            result = await self._request('GET', f'/prices/latest/{token_id}')

            price_data = result.get('data', {})
            if price_data and 'price' in price_data:
                return Decimal(str(price_data['price']))

            return None

        except Exception as e:
            logger.error(f"❌ Error fetching Opinion price {token_id}: {e}")
            return None

    async def get_price_history(
        self,
        token_id: str,
        interval: str = '1h',
        start_at: Optional[int] = None,
        end_at: Optional[int] = None
    ) -> List[Dict]:
        """
        Get price history (candlestick data)

        Args:
            token_id: Token ID
            interval: '1m', '1h', '1d', '1w', 'max'
            start_at: Start timestamp
            end_at: End timestamp
        """
        try:
            params = {'interval': interval}
            if start_at:
                params['start_at'] = start_at
            if end_at:
                params['end_at'] = end_at

            result = await self._request(
                'GET',
                f'/prices/history/{token_id}',
                params=params
            )

            return result.get('data', [])

        except Exception as e:
            logger.error(f"❌ Error fetching Opinion price history: {e}")
            return []

    async def get_fee_rates(self, token_id: str) -> Dict[str, Decimal]:
        """Get trading fee rates for a token"""
        try:
            result = await self._request('GET', f'/fees/{token_id}')

            fees = result.get('data', {})
            return {
                'maker_fee': Decimal(str(fees.get('maker_fee', 0))),
                'taker_fee': Decimal(str(fees.get('taker_fee', 0)))
            }

        except Exception as e:
            logger.error(f"❌ Error fetching Opinion fees: {e}")
            return {'maker_fee': Decimal('0'), 'taker_fee': Decimal('0')}

    async def get_top_markets(self, limit: int = 20) -> List[OpinionMarket]:
        """Get top markets by volume"""
        markets = await self.get_markets(limit=limit)
        # Sort by volume
        markets.sort(key=lambda m: m.volume, reverse=True)
        return markets[:limit]

    async def close(self):
        """Close session"""
        if self.session:
            await self.session.close()
            logger.info("✅ Opinion REST client closed")


# ===========================
# Opinion WebSocket Client
# ===========================

class OpinionWebSocketClient:
    """Opinion.trade WebSocket client for real-time data"""

    WS_URL = "wss://ws.opinion.trade"

    def __init__(
        self,
        api_key: Optional[str] = None,
        on_orderbook: Optional[Callable] = None,
        on_trade: Optional[Callable] = None,
        on_price_update: Optional[Callable] = None
    ):
        self.api_key = api_key
        self.on_orderbook = on_orderbook
        self.on_trade = on_trade
        self.on_price_update = on_price_update

        self.rest_client = OpinionRestClient(api_key)
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.running = False
        self.subscribed_tokens: set = set()

    async def initialize(self):
        """Initialize REST client"""
        await self.rest_client.initialize()
        self.session = aiohttp.ClientSession()
        logger.info("✅ Opinion WebSocket client initialized")

    async def connect(self):
        """Connect to WebSocket"""
        try:
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'

            self.ws = await self.session.ws_connect(
                self.WS_URL,
                headers=headers,
                heartbeat=30
            )

            logger.info("✅ Connected to Opinion WebSocket")
            return True

        except Exception as e:
            logger.error(f"❌ Opinion WebSocket connection failed: {e}")
            return False

    async def subscribe_orderbook(self, token_id: str):
        """Subscribe to orderbook updates"""
        if not self.ws:
            logger.warning("WebSocket not connected")
            return

        try:
            await self.ws.send_json({
                'type': 'subscribe',
                'channel': 'orderbook',
                'token_id': token_id
            })

            self.subscribed_tokens.add(token_id)
            logger.info(f"📡 Subscribed to Opinion orderbook: {token_id}")

        except Exception as e:
            logger.error(f"❌ Subscription error: {e}")

    async def subscribe_trades(self, token_id: str):
        """Subscribe to trade updates"""
        if not self.ws:
            logger.warning("WebSocket not connected")
            return

        try:
            await self.ws.send_json({
                'type': 'subscribe',
                'channel': 'trades',
                'token_id': token_id
            })

            logger.info(f"📡 Subscribed to Opinion trades: {token_id}")

        except Exception as e:
            logger.error(f"❌ Subscription error: {e}")

    async def subscribe_top_markets(self, limit: int = 10):
        """Subscribe to top markets"""
        top_markets = await self.rest_client.get_top_markets(limit)

        for market in top_markets:
            # Subscribe to both YES and NO tokens
            if market.token_yes_id:
                await self.subscribe_orderbook(market.token_yes_id)
                await self.subscribe_trades(market.token_yes_id)
                await asyncio.sleep(0.1)

            if market.token_no_id:
                await self.subscribe_orderbook(market.token_no_id)
                await self.subscribe_trades(market.token_no_id)
                await asyncio.sleep(0.1)

        logger.info(f"✅ Subscribed to {len(top_markets)} top Opinion markets")

    async def start(self):
        """Start WebSocket listener"""
        self.running = True

        while self.running:
            try:
                if not self.ws or self.ws.closed:
                    await self.connect()
                    await asyncio.sleep(1)
                    continue

                async for msg in self.ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        await self._handle_message(json.loads(msg.data))
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f"WebSocket error: {self.ws.exception()}")
                        break

                # Reconnect if disconnected
                logger.warning("WebSocket disconnected, reconnecting...")
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await asyncio.sleep(5)

    async def _handle_message(self, data: Dict):
        """Handle WebSocket message"""
        try:
            channel = data.get('channel')

            if channel == 'orderbook' and self.on_orderbook:
                await self._handle_orderbook_update(data)
            elif channel == 'trade' and self.on_trade:
                await self._handle_trade(data)
            elif channel == 'price' and self.on_price_update:
                await self._handle_price_update(data)

        except Exception as e:
            logger.error(f"Message handling error: {e}")

    async def _handle_orderbook_update(self, data: Dict):
        """Handle orderbook update"""
        orderbook = OpinionOrderbook(
            token_id=data['token_id'],
            market_id=data.get('market_id', ''),
            bids=data.get('bids', []),
            asks=data.get('asks', []),
            timestamp=datetime.now()
        )

        await self.on_orderbook(orderbook)

    async def _handle_trade(self, data: Dict):
        """Handle trade update"""
        trade = OpinionTrade(
            trade_id=data.get('trade_id', ''),
            market_id=data.get('market_id', ''),
            token_id=data['token_id'],
            side=data['side'],
            price=Decimal(str(data['price'])),
            size=Decimal(str(data['size'])),
            timestamp=datetime.fromtimestamp(data['timestamp'])
        )

        await self.on_trade(trade)

    async def _handle_price_update(self, data: Dict):
        """Handle price update"""
        await self.on_price_update(data)

    async def stop(self):
        """Stop WebSocket"""
        self.running = False

        if self.ws:
            await self.ws.close()

        if self.session:
            await self.session.close()

        await self.rest_client.close()

        logger.info("✅ Opinion WebSocket client stopped")


# ===========================
# Demo/Testing
# ===========================

async def demo():
    """Demo Opinion client"""

    # Optional: Replace with your API key for authenticated endpoints
    api_key = None  # "your_api_key_here"

    # REST client demo
    print("\n" + "="*60)
    print("🔹 Opinion.trade REST Client Demo")
    print("="*60)

    rest_client = OpinionRestClient(api_key)
    await rest_client.initialize()

    # Get top markets
    markets = await rest_client.get_top_markets(limit=5)
    print(f"\n📊 Top 5 Opinion Markets by Volume:")
    for i, market in enumerate(markets, 1):
        print(f"{i}. {market.title}")
        print(f"   Market ID: {market.market_id}")
        print(f"   YES: ${market.yes_price:.4f}" if market.yes_price else "   YES: N/A")
        print(f"   NO: ${market.no_price:.4f}" if market.no_price else "   NO: N/A")
        print(f"   Volume: ${market.volume:,.0f}")
        print(f"   Liquidity: ${market.liquidity:,.0f}")
        print()

    # Get orderbook
    if markets and markets[0].token_yes_id:
        token_id = markets[0].token_yes_id
        orderbook = await rest_client.get_orderbook(token_id)
        if orderbook:
            print(f"\n📈 Orderbook for token {token_id}:")
            print(f"Best Bid: ${orderbook.get_best_bid():.4f}" if orderbook.get_best_bid() else "Best Bid: N/A")
            print(f"Best Ask: ${orderbook.get_best_ask():.4f}" if orderbook.get_best_ask() else "Best Ask: N/A")
            print(f"Bid depth: {len(orderbook.bids)} levels")
            print(f"Ask depth: {len(orderbook.asks)} levels")

    await rest_client.close()

    # WebSocket demo
    print("\n" + "="*60)
    print("🔹 Opinion WebSocket Demo (10 seconds)")
    print("="*60)

    async def on_orderbook(ob: OpinionOrderbook):
        print(f"📊 Orderbook update: {ob.token_id}")

    async def on_trade(trade: OpinionTrade):
        print(f"💰 Trade: {trade.side} {trade.size} @ ${trade.price:.4f}")

    ws_client = OpinionWebSocketClient(
        api_key,
        on_orderbook=on_orderbook,
        on_trade=on_trade
    )
    await ws_client.initialize()
    await ws_client.connect()
    await ws_client.subscribe_top_markets(limit=2)

    # Listen for 10 seconds
    listener = asyncio.create_task(ws_client.start())
    await asyncio.sleep(10)

    await ws_client.stop()
    listener.cancel()

    print("\n✅ Demo completed!")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    asyncio.run(demo())
