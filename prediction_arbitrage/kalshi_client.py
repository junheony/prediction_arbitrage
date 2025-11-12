"""
Kalshi REST + WebSocket Client
Real-time market data and trading for Kalshi prediction markets
"""

import asyncio
import aiohttp
import logging
from typing import Optional, Callable, Dict, List, Any
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass
import json
import time

logger = logging.getLogger(__name__)

# ===========================
# Data Models
# ===========================

@dataclass
class KalshiMarket:
    """Kalshi market structure"""
    ticker: str
    title: str
    event_ticker: str
    category: str
    close_time: datetime
    yes_bid: Optional[Decimal] = None
    yes_ask: Optional[Decimal] = None
    no_bid: Optional[Decimal] = None
    no_ask: Optional[Decimal] = None
    volume: Decimal = Decimal('0')
    open_interest: Decimal = Decimal('0')
    last_price: Optional[Decimal] = None

    @property
    def best_yes_price(self) -> Optional[Decimal]:
        """Best YES price (ask for buying YES)"""
        return self.yes_ask

    @property
    def best_no_price(self) -> Optional[Decimal]:
        """Best NO price (ask for buying NO)"""
        return self.no_ask


@dataclass
class KalshiOrderbook:
    """Kalshi orderbook structure"""
    ticker: str
    yes_bids: List[Dict[str, Any]]  # [{'price': cents, 'quantity': shares}]
    yes_asks: List[Dict[str, Any]]
    no_bids: List[Dict[str, Any]]
    no_asks: List[Dict[str, Any]]
    timestamp: datetime

    def get_best_yes_bid(self) -> Optional[Decimal]:
        """Get best YES bid price"""
        if self.yes_bids:
            return Decimal(str(self.yes_bids[0]['price'])) / 100
        return None

    def get_best_yes_ask(self) -> Optional[Decimal]:
        """Get best YES ask price"""
        if self.yes_asks:
            return Decimal(str(self.yes_asks[0]['price'])) / 100
        return None

    def get_best_no_bid(self) -> Optional[Decimal]:
        """Get best NO bid price"""
        if self.no_bids:
            return Decimal(str(self.no_bids[0]['price'])) / 100
        return None

    def get_best_no_ask(self) -> Optional[Decimal]:
        """Get best NO ask price"""
        if self.no_asks:
            return Decimal(str(self.no_asks[0]['price'])) / 100
        return None


# ===========================
# Kalshi REST Client
# ===========================

class KalshiRestClient:
    """Kalshi REST API client"""

    BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.session: Optional[aiohttp.ClientSession] = None
        self.token: Optional[str] = None
        self.token_expires_at: float = 0

    async def initialize(self):
        """Initialize session and login"""
        self.session = aiohttp.ClientSession()
        await self._login()
        logger.info("✅ Kalshi REST client initialized")

    async def _login(self):
        """Login and get auth token"""
        try:
            async with self.session.post(
                f"{self.BASE_URL}/login",
                json={"email": self.email, "password": self.password}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.token = data.get('token')
                    # Token expires in 30 minutes
                    self.token_expires_at = time.time() + 1800
                    logger.info("✅ Kalshi login successful")
                else:
                    error = await resp.text()
                    logger.error(f"❌ Kalshi login failed: {error}")
                    raise Exception(f"Kalshi login failed: {error}")
        except Exception as e:
            logger.error(f"❌ Kalshi login error: {e}")
            raise

    async def _ensure_auth(self):
        """Ensure token is valid, refresh if needed"""
        if time.time() >= self.token_expires_at - 60:  # Refresh 1 min before expiry
            logger.info("🔄 Refreshing Kalshi token...")
            await self._login()

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make authenticated request"""
        await self._ensure_auth()

        headers = kwargs.pop('headers', {})
        headers['Authorization'] = f'Bearer {self.token}'

        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"

        async with self.session.request(method, url, headers=headers, **kwargs) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                error = await resp.text()
                logger.error(f"❌ Kalshi API error: {error}")
                raise Exception(f"Kalshi API error: {error}")

    async def get_markets(self, limit: int = 100, status: str = "open") -> List[KalshiMarket]:
        """Get list of active markets"""
        try:
            data = await self._request('GET', '/markets', params={
                'limit': limit,
                'status': status
            })

            markets = []
            for m in data.get('markets', []):
                market = KalshiMarket(
                    ticker=m['ticker'],
                    title=m['title'],
                    event_ticker=m['event_ticker'],
                    category=m.get('category', ''),
                    close_time=datetime.fromisoformat(m['close_time'].replace('Z', '+00:00')),
                    yes_bid=Decimal(str(m.get('yes_bid', 0))) / 100 if m.get('yes_bid') else None,
                    yes_ask=Decimal(str(m.get('yes_ask', 0))) / 100 if m.get('yes_ask') else None,
                    volume=Decimal(str(m.get('volume', 0))),
                    open_interest=Decimal(str(m.get('open_interest', 0))),
                    last_price=Decimal(str(m.get('last_price', 0))) / 100 if m.get('last_price') else None
                )
                markets.append(market)

            logger.info(f"📊 Retrieved {len(markets)} Kalshi markets")
            return markets

        except Exception as e:
            logger.error(f"❌ Error fetching Kalshi markets: {e}")
            return []

    async def get_market(self, ticker: str) -> Optional[KalshiMarket]:
        """Get single market details"""
        try:
            data = await self._request('GET', f'/markets/{ticker}')
            m = data.get('market', {})

            return KalshiMarket(
                ticker=m['ticker'],
                title=m['title'],
                event_ticker=m['event_ticker'],
                category=m.get('category', ''),
                close_time=datetime.fromisoformat(m['close_time'].replace('Z', '+00:00')),
                yes_bid=Decimal(str(m.get('yes_bid', 0))) / 100 if m.get('yes_bid') else None,
                yes_ask=Decimal(str(m.get('yes_ask', 0))) / 100 if m.get('yes_ask') else None,
                volume=Decimal(str(m.get('volume', 0))),
                open_interest=Decimal(str(m.get('open_interest', 0))),
                last_price=Decimal(str(m.get('last_price', 0))) / 100 if m.get('last_price') else None
            )
        except Exception as e:
            logger.error(f"❌ Error fetching Kalshi market {ticker}: {e}")
            return None

    async def get_orderbook(self, ticker: str) -> Optional[KalshiOrderbook]:
        """Get orderbook for a market"""
        try:
            data = await self._request('GET', f'/markets/{ticker}/orderbook')
            ob = data.get('orderbook', {})

            return KalshiOrderbook(
                ticker=ticker,
                yes_bids=ob.get('yes', {}).get('bids', []),
                yes_asks=ob.get('yes', {}).get('asks', []),
                no_bids=ob.get('no', {}).get('bids', []),
                no_asks=ob.get('no', {}).get('asks', []),
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"❌ Error fetching Kalshi orderbook {ticker}: {e}")
            return None

    async def get_top_markets(self, limit: int = 20) -> List[KalshiMarket]:
        """Get top markets by volume"""
        markets = await self.get_markets(limit=limit)
        # Sort by volume
        markets.sort(key=lambda m: m.volume, reverse=True)
        return markets[:limit]

    async def close(self):
        """Close session"""
        if self.session:
            await self.session.close()
            logger.info("✅ Kalshi REST client closed")


# ===========================
# Kalshi WebSocket Client
# ===========================

class KalshiWebSocketClient:
    """Kalshi WebSocket client for real-time data"""

    WS_URL = "wss://api.elections.kalshi.com/trade-api/ws/v2"

    def __init__(
        self,
        email: str,
        password: str,
        on_orderbook: Optional[Callable] = None,
        on_trade: Optional[Callable] = None,
        on_market_update: Optional[Callable] = None
    ):
        self.email = email
        self.password = password
        self.on_orderbook = on_orderbook
        self.on_trade = on_trade
        self.on_market_update = on_market_update

        self.rest_client = KalshiRestClient(email, password)
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.running = False
        self.subscribed_tickers: set = set()

    async def initialize(self):
        """Initialize REST client and get token"""
        await self.rest_client.initialize()
        self.session = aiohttp.ClientSession()
        logger.info("✅ Kalshi WebSocket client initialized")

    async def connect(self):
        """Connect to WebSocket"""
        try:
            # Connect with auth token
            headers = {
                'Authorization': f'Bearer {self.rest_client.token}'
            }

            self.ws = await self.session.ws_connect(
                self.WS_URL,
                headers=headers,
                heartbeat=30
            )

            logger.info("✅ Connected to Kalshi WebSocket")
            return True

        except Exception as e:
            logger.error(f"❌ Kalshi WebSocket connection failed: {e}")
            return False

    async def subscribe_market(self, ticker: str):
        """Subscribe to market updates"""
        if not self.ws:
            logger.warning("WebSocket not connected")
            return

        try:
            await self.ws.send_json({
                'type': 'subscribe',
                'channels': ['orderbook', 'trades'],
                'market_ticker': ticker
            })

            self.subscribed_tickers.add(ticker)
            logger.info(f"📡 Subscribed to Kalshi market: {ticker}")

        except Exception as e:
            logger.error(f"❌ Subscription error: {e}")

    async def subscribe_top_markets(self, limit: int = 10):
        """Subscribe to top markets by volume"""
        top_markets = await self.rest_client.get_top_markets(limit)

        for market in top_markets:
            await self.subscribe_market(market.ticker)
            await asyncio.sleep(0.1)  # Rate limiting

        logger.info(f"✅ Subscribed to {len(top_markets)} top Kalshi markets")

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
            msg_type = data.get('type')

            if msg_type == 'orderbook_update' and self.on_orderbook:
                await self._handle_orderbook_update(data)
            elif msg_type == 'trade' and self.on_trade:
                await self._handle_trade(data)
            elif msg_type == 'market_update' and self.on_market_update:
                await self._handle_market_update(data)

        except Exception as e:
            logger.error(f"Message handling error: {e}")

    async def _handle_orderbook_update(self, data: Dict):
        """Handle orderbook update"""
        orderbook = KalshiOrderbook(
            ticker=data['ticker'],
            yes_bids=data.get('yes_bids', []),
            yes_asks=data.get('yes_asks', []),
            no_bids=data.get('no_bids', []),
            no_asks=data.get('no_asks', []),
            timestamp=datetime.now()
        )

        await self.on_orderbook(orderbook)

    async def _handle_trade(self, data: Dict):
        """Handle trade update"""
        await self.on_trade(data)

    async def _handle_market_update(self, data: Dict):
        """Handle market update"""
        await self.on_market_update(data)

    async def stop(self):
        """Stop WebSocket"""
        self.running = False

        if self.ws:
            await self.ws.close()

        if self.session:
            await self.session.close()

        await self.rest_client.close()

        logger.info("✅ Kalshi WebSocket client stopped")


# ===========================
# Demo/Testing
# ===========================

async def demo():
    """Demo Kalshi client"""

    # Replace with your credentials
    email = "your_email@example.com"
    password = "your_password"

    # REST client demo
    print("\n" + "="*60)
    print("🔹 Kalshi REST Client Demo")
    print("="*60)

    rest_client = KalshiRestClient(email, password)
    await rest_client.initialize()

    # Get top markets
    markets = await rest_client.get_top_markets(limit=5)
    print(f"\n📊 Top 5 Kalshi Markets by Volume:")
    for i, market in enumerate(markets, 1):
        print(f"{i}. {market.title}")
        print(f"   Ticker: {market.ticker}")
        print(f"   YES: {market.yes_bid} / {market.yes_ask}")
        print(f"   Volume: ${market.volume:,.0f}")
        print()

    # Get orderbook
    if markets:
        ticker = markets[0].ticker
        orderbook = await rest_client.get_orderbook(ticker)
        if orderbook:
            print(f"\n📈 Orderbook for {ticker}:")
            print(f"YES Best Bid: {orderbook.get_best_yes_bid()}")
            print(f"YES Best Ask: {orderbook.get_best_yes_ask()}")
            print(f"NO Best Bid: {orderbook.get_best_no_bid()}")
            print(f"NO Best Ask: {orderbook.get_best_no_ask()}")

    await rest_client.close()

    # WebSocket demo
    print("\n" + "="*60)
    print("🔹 Kalshi WebSocket Demo (10 seconds)")
    print("="*60)

    async def on_orderbook(ob: KalshiOrderbook):
        print(f"📊 Orderbook update: {ob.ticker}")

    ws_client = KalshiWebSocketClient(email, password, on_orderbook=on_orderbook)
    await ws_client.initialize()
    await ws_client.connect()
    await ws_client.subscribe_top_markets(limit=3)

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
