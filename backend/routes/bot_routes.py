"""Bot control routes"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy import select, delete, update

from models import BotStartRequest, BotStatus, ArbitrageOpportunity, BotConfig
from auth import get_current_active_user
from bot_manager import bot_manager
from database import async_session, opportunities

router = APIRouter(prefix="/api/bot", tags=["bot"])


@router.post("/start")
async def start_bot(
    request: BotStartRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Start the arbitrage bot"""
    config = request.config if request.config else BotConfig()

    try:
        await bot_manager.start_bot(current_user["id"], config)
        return {"message": "Bot started successfully", "config": config.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_bot(current_user: dict = Depends(get_current_active_user)):
    """Stop the arbitrage bot"""
    try:
        await bot_manager.stop_bot(current_user["id"])
        return {"message": "Bot stopped successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=BotStatus)
async def get_bot_status(current_user: dict = Depends(get_current_active_user)):
    """Get bot status"""
    try:
        status = await bot_manager.get_bot_status(current_user["id"])
        return BotStatus(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/opportunities", response_model=List[ArbitrageOpportunity])
async def get_opportunities(
    limit: int = 50,
    current_user: dict = Depends(get_current_active_user)
):
    """Get recent arbitrage opportunities"""
    try:
        async with async_session() as session:
            result = await session.execute(
                select(opportunities)
                .where(opportunities.c.user_id == current_user["id"])
                .order_by(opportunities.c.timestamp.desc())
                .limit(limit)
            )
            results = result.fetchall()
            return [ArbitrageOpportunity(**dict(r._mapping)) for r in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/opportunities/{opportunity_id}")
async def delete_opportunity(
    opportunity_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Delete an opportunity"""
    try:
        async with async_session() as session:
            # Verify ownership
            result = await session.execute(
                select(opportunities).where(
                    opportunities.c.id == opportunity_id,
                    opportunities.c.user_id == current_user["id"]
                )
            )
            opp = result.first()

            if not opp:
                raise HTTPException(status_code=404, detail="Opportunity not found")

            # Delete
            await session.execute(
                delete(opportunities).where(opportunities.c.id == opportunity_id)
            )
            await session.commit()

            return {"message": "Opportunity deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/opportunities/{opportunity_id}/execute")
async def execute_opportunity(
    opportunity_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Mark opportunity as executed (in future, will place actual orders)"""
    try:
        async with async_session() as session:
            # Verify ownership
            result = await session.execute(
                select(opportunities).where(
                    opportunities.c.id == opportunity_id,
                    opportunities.c.user_id == current_user["id"]
                )
            )
            opp = result.first()

            if not opp:
                raise HTTPException(status_code=404, detail="Opportunity not found")

            # Mark as executed
            await session.execute(
                update(opportunities)
                .where(opportunities.c.id == opportunity_id)
                .values(executed=True)
            )
            await session.commit()

            return {"message": "Opportunity marked as executed", "opportunity_id": opportunity_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
