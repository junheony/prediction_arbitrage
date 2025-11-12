"""Bot manager to handle multiple user bot instances"""
import asyncio
import sys
import os
from typing import Dict, Optional, Set
from datetime import datetime
from decimal import Decimal
import logging

# Add parent directory to path to import bot
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'prediction_arbitrage'))

from database import database, bot_sessions, opportunities
from models import BotConfig, ArbitrageOpportunity

logger = logging.getLogger(__name__)


class UserBotInstance:
    """Individual bot instance for a user"""

    def __init__(self, user_id: int, config: BotConfig, ws_manager):
        self.user_id = user_id
        self.config = config
        self.ws_manager = ws_manager
        self.status = "stopped"
        self.task: Optional[asyncio.Task] = None
        self.opportunities_found = 0
        self.total_profit = Decimal("0.0")
        self.started_at: Optional[datetime] = None
        self.session_id: Optional[int] = None

    async def start(self):
        """Start the bot"""
        if self.status == "running":
            return

        self.status = "running"
        self.started_at = datetime.utcnow()

        # Create bot session in database
        query = bot_sessions.insert().values(
            user_id=self.user_id,
            status="running",
            config=self.config.model_dump(),
            started_at=self.started_at,
            opportunities_found=0,
            total_profit="0.0"
        )
        self.session_id = await database.execute(query)

        # Start monitoring task
        self.task = asyncio.create_task(self._monitor_markets())

        # Send status update via WebSocket
        await self.ws_manager.send_to_user(self.user_id, {
            "type": "status",
            "data": {
                "status": "running",
                "started_at": self.started_at.isoformat(),
                "config": self.config.model_dump()
            }
        })

    async def stop(self):
        """Stop the bot"""
        if self.status != "running":
            return

        self.status = "stopped"

        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        # Update bot session in database
        if self.session_id:
            query = bot_sessions.update().where(
                bot_sessions.c.id == self.session_id
            ).values(
                status="stopped",
                stopped_at=datetime.utcnow(),
                opportunities_found=self.opportunities_found,
                total_profit=str(self.total_profit)
            )
            await database.execute(query)

        # Send status update via WebSocket
        await self.ws_manager.send_to_user(self.user_id, {
            "type": "status",
            "data": {
                "status": "stopped",
                "opportunities_found": self.opportunities_found,
                "total_profit": str(self.total_profit)
            }
        })

    async def _monitor_markets(self):
        """Monitor markets for arbitrage opportunities"""
        try:
            # Import bot clients
            from kalshi_client import KalshiRestClient, KalshiWebSocketClient
            from opinion_client import OpinionRestClient, OpinionWebSocketClient
            from polymarket_websocket import PolymarketWebSocketClient

            logger.info(f"Starting bot for user {self.user_id}")

            # Initialize clients based on config
            clients = {}
            if "polymarket" in self.config.platforms:
                # Would initialize with user's credentials
                pass

            if "kalshi" in self.config.platforms:
                kalshi_email = os.getenv("KALSHI_EMAIL")
                kalshi_password = os.getenv("KALSHI_PASSWORD")
                if kalshi_email and kalshi_password:
                    clients["kalshi"] = KalshiRestClient(kalshi_email, kalshi_password)

            if "opinion" in self.config.platforms:
                opinion_key = os.getenv("OPINION_API_KEY")
                clients["opinion"] = OpinionRestClient(opinion_key)

            # Simplified monitoring loop
            while self.status == "running":
                try:
                    # Scan for opportunities
                    await self._scan_opportunities(clients)
                    await asyncio.sleep(5)  # Check every 5 seconds

                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    await asyncio.sleep(10)

        except asyncio.CancelledError:
            logger.info(f"Bot monitoring cancelled for user {self.user_id}")
        except Exception as e:
            logger.error(f"Fatal error in bot: {e}")
            self.status = "error"
            await self.ws_manager.send_to_user(self.user_id, {
                "type": "error",
                "data": {"message": str(e)}
            })

    async def _scan_opportunities(self, clients: Dict):
        """Scan for arbitrage opportunities"""
        try:
            opportunities_found = []

            # Example: Check Kalshi vs Opinion
            if "kalshi" in clients and "opinion" in clients:
                kalshi_client = clients["kalshi"]
                opinion_client = clients["opinion"]

                # Get top markets from each
                kalshi_markets = await kalshi_client.get_top_markets(limit=5)
                opinion_markets = await opinion_client.get_markets()

                # Simple comparison (in production, would use matching engine)
                for k_market in kalshi_markets[:3]:
                    for o_market in opinion_markets[:3]:
                        # Simulate opportunity detection
                        profit = self._calculate_profit(k_market, o_market)

                        if profit and profit > Decimal(str(self.config.min_profit_threshold)):
                            opp = {
                                "platform_a": "kalshi",
                                "platform_b": "opinion",
                                "market_a": k_market.get("ticker", "Unknown"),
                                "market_b": o_market.get("question", "Unknown"),
                                "profit_percentage": f"{float(profit * 100):.2f}",
                                "suggested_action": f"Buy on Kalshi at {k_market.get('yes_bid', 0)}, Sell on Opinion",
                                "timestamp": datetime.utcnow(),
                                "executed": False
                            }
                            opportunities_found.append(opp)

            # Save and notify about opportunities
            for opp in opportunities_found:
                self.opportunities_found += 1

                # Save to database
                query = opportunities.insert().values(
                    user_id=self.user_id,
                    **opp
                )
                opp_id = await database.execute(query)
                opp["id"] = opp_id

                # Send via WebSocket
                await self.ws_manager.send_to_user(self.user_id, {
                    "type": "opportunity",
                    "data": opp
                })

        except Exception as e:
            logger.error(f"Error scanning opportunities: {e}")

    def _calculate_profit(self, market_a: Dict, market_b: Dict) -> Optional[Decimal]:
        """Calculate potential profit (simplified)"""
        try:
            # This is a simplified calculation
            # In production, would use the full fee-aware calculator
            return Decimal("0.025")  # Example 2.5% profit
        except:
            return None


class BotManager:
    """Manages multiple bot instances"""

    def __init__(self):
        self.bots: Dict[int, UserBotInstance] = {}
        self.ws_manager = None

    def set_ws_manager(self, ws_manager):
        """Set WebSocket manager"""
        self.ws_manager = ws_manager

    async def start_bot(self, user_id: int, config: BotConfig):
        """Start a bot for a user"""
        if user_id in self.bots:
            await self.stop_bot(user_id)

        bot = UserBotInstance(user_id, config, self.ws_manager)
        self.bots[user_id] = bot
        await bot.start()

    async def stop_bot(self, user_id: int):
        """Stop a bot for a user"""
        if user_id in self.bots:
            await self.bots[user_id].stop()
            del self.bots[user_id]

    async def get_bot_status(self, user_id: int) -> Dict:
        """Get bot status for a user"""
        if user_id not in self.bots:
            # Check database for last session
            query = bot_sessions.select().where(
                bot_sessions.c.user_id == user_id
            ).order_by(bot_sessions.c.id.desc()).limit(1)

            last_session = await database.fetch_one(query)

            if last_session:
                return {
                    "status": last_session["status"],
                    "started_at": last_session["started_at"],
                    "stopped_at": last_session["stopped_at"],
                    "opportunities_found": last_session["opportunities_found"],
                    "total_profit": last_session["total_profit"],
                    "config": last_session["config"]
                }

            return {
                "status": "stopped",
                "opportunities_found": 0,
                "total_profit": "0.0"
            }

        bot = self.bots[user_id]
        return {
            "status": bot.status,
            "started_at": bot.started_at,
            "opportunities_found": bot.opportunities_found,
            "total_profit": str(bot.total_profit),
            "config": bot.config.model_dump()
        }

    async def stop_all(self):
        """Stop all bots"""
        for user_id in list(self.bots.keys()):
            await self.stop_bot(user_id)


# Global bot manager instance
bot_manager = BotManager()
