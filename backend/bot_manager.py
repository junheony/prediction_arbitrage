"""Bot manager to handle multiple user bot instances"""
import asyncio
import sys
import os
from typing import Dict, Optional, Set
from datetime import datetime
from decimal import Decimal
import logging
from sqlalchemy import select, insert, update

# Add parent directory to path to import bot
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'prediction_arbitrage'))

from database import async_session, bot_sessions, opportunities
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
        async with async_session() as session:
            result = await session.execute(
                insert(bot_sessions).values(
                    user_id=self.user_id,
                    status="running",
                    config=self.config.model_dump(),
                    started_at=self.started_at,
                    opportunities_found=0,
                    total_profit="0.0"
                )
            )
            await session.commit()
            self.session_id = result.inserted_primary_key[0]

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
            async with async_session() as session:
                await session.execute(
                    update(bot_sessions)
                    .where(bot_sessions.c.id == self.session_id)
                    .values(
                        status="stopped",
                        stopped_at=datetime.utcnow(),
                        opportunities_found=self.opportunities_found,
                        total_profit=str(self.total_profit)
                    )
                )
                await session.commit()

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
            logger.info(f"Starting bot for user {self.user_id}")

            # Simplified monitoring loop
            while self.status == "running":
                try:
                    # Scan for opportunities (simplified)
                    await self._scan_opportunities()
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

    async def _scan_opportunities(self):
        """Scan for arbitrage opportunities (simplified for demo)"""
        try:
            # Example: Create simulated opportunities
            # In production, would use actual API clients
            import random

            if random.random() < 0.1:  # 10% chance per scan
                platforms = ["polymarket", "kalshi", "opinion"]
                platform_a, platform_b = random.sample(platforms, 2)
                profit = Decimal(str(round(random.uniform(1.5, 5.0), 2)))

                opp = {
                    "user_id": self.user_id,
                    "platform_a": platform_a,
                    "platform_b": platform_b,
                    "market_a": f"Sample market on {platform_a}",
                    "market_b": f"Sample market on {platform_b}",
                    "profit_percentage": str(profit),
                    "suggested_action": f"Buy on {platform_a}, Sell on {platform_b}",
                    "timestamp": datetime.utcnow(),
                    "executed": False
                }

                self.opportunities_found += 1
                self.total_profit += profit

                # Save to database
                async with async_session() as session:
                    result = await session.execute(insert(opportunities).values(**opp))
                    await session.commit()
                    opp["id"] = result.inserted_primary_key[0]

                # Send via WebSocket
                await self.ws_manager.send_to_user(self.user_id, {
                    "type": "opportunity",
                    "data": opp
                })

        except Exception as e:
            logger.error(f"Error scanning opportunities: {e}")


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
            async with async_session() as session:
                result = await session.execute(
                    select(bot_sessions)
                    .where(bot_sessions.c.user_id == user_id)
                    .order_by(bot_sessions.c.id.desc())
                    .limit(1)
                )
                last_session = result.first()

                if last_session:
                    ls = dict(last_session._mapping)
                    return {
                        "status": ls["status"],
                        "started_at": ls["started_at"],
                        "stopped_at": ls["stopped_at"],
                        "opportunities_found": ls["opportunities_found"],
                        "total_profit": ls["total_profit"],
                        "config": ls["config"]
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
