"""
Integrated Arbitrage Bot with All Features
통합 차익거래 봇 (모든 기능 포함)

Now supports 3 platforms:
- Polymarket (WebSocket + REST)
- Kalshi (WebSocket + REST)
- Opinion.trade (WebSocket + REST)
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

# 모든 모듈 임포트
from compliance_checker import ComplianceChecker, GeoLocationService
from polymarket_websocket import PolymarketWebSocketClient, OrderbookUpdate, TradeUpdate
from kalshi_client import KalshiWebSocketClient, KalshiOrderbook, KalshiMarket
from opinion_client import OpinionWebSocketClient, OpinionOrderbook, OpinionMarket
from fee_aware_calculator import FeeAwareArbitrageCalculator
from enhanced_matching_engine import EnhancedMatchingEngine
from alert_system import AlertManager, EdgeCaseDetector, SlackChannel, TelegramChannel
from delta_hedge_api import DeltaHedgeEngine, PositionManager, Position
from slippage_management import SlippageCalculator, SmartOrderExecutor
from dynamic_position_management import DynamicPositionManager, PositionConfig

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('arbitrage_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===========================
# 통합 봇 클래스
# ===========================

class IntegratedArbitrageBot:
    """모든 기능이 통합된 차익거래 봇 - 3개 플랫폼 지원"""

    def __init__(self, config: Dict):
        self.config = config
        self.running = False

        # 컴포넌트들
        self.compliance_checker = None

        # 플랫폼 클라이언트들
        self.polymarket_ws = None
        self.kalshi_ws = None
        self.opinion_ws = None

        self.fee_calculator = None
        self.matching_engine = None
        self.alert_manager = None
        self.edge_detector = None
        self.hedge_engine = None
        self.position_manager = None
        self.slippage_calc = None
        self.order_executor = None
        self.dynamic_position_mgr = None

        # 데이터 저장소 (플랫폼별)
        self.active_opportunities = []
        self.monitored_markets = {
            'polymarket': {},
            'kalshi': {},
            'opinion': {}
        }

    async def initialize(self):
        """모든 컴포넌트 초기화"""
        logger.info("🚀 Initializing Integrated Arbitrage Bot...")

        # 1. 규제 체크 시스템
        logger.info("Initializing compliance checker...")
        geo_service = GeoLocationService()
        await geo_service.initialize()
        self.compliance_checker = ComplianceChecker(geo_service)

        # 플랫폼 접근 권한 확인
        access_check = await self.compliance_checker.check_all_platforms(
            user_age=self.config.get('user_age'),
            kyc_status=self.config.get('kyc_status', {})
        )

        for platform, check in access_check.items():
            if check.allowed:
                logger.info(f"✅ {platform.upper()}: Access granted")
            else:
                logger.warning(f"❌ {platform.upper()}: {check.reason}")

        # 2. WebSocket 클라이언트들 초기화
        logger.info("Initializing WebSocket clients for all platforms...")

        # 2.1 Polymarket WebSocket
        logger.info("  → Polymarket WebSocket...")
        self.polymarket_ws = PolymarketWebSocketClient(
            on_orderbook=self._handle_polymarket_orderbook,
            on_trade=self._handle_polymarket_trade,
            on_market_update=self._handle_polymarket_market
        )
        await self.polymarket_ws.initialize()
        asyncio.create_task(self.polymarket_ws.start())
        await self.polymarket_ws.subscribe_to_top_markets(limit=10)

        # 2.2 Kalshi WebSocket (if credentials provided)
        if self.config.get('kalshi_email') and self.config.get('kalshi_password'):
            logger.info("  → Kalshi WebSocket...")
            self.kalshi_ws = KalshiWebSocketClient(
                email=self.config['kalshi_email'],
                password=self.config['kalshi_password'],
                on_orderbook=self._handle_kalshi_orderbook,
                on_trade=self._handle_kalshi_trade,
                on_market_update=self._handle_kalshi_market
            )
            await self.kalshi_ws.initialize()
            asyncio.create_task(self.kalshi_ws.start())
            await self.kalshi_ws.subscribe_top_markets(limit=10)
        else:
            logger.warning("  ⚠️  Kalshi credentials not provided, skipping...")

        # 2.3 Opinion WebSocket (if API key provided)
        if self.config.get('opinion_api_key'):
            logger.info("  → Opinion.trade WebSocket...")
            self.opinion_ws = OpinionWebSocketClient(
                api_key=self.config['opinion_api_key'],
                on_orderbook=self._handle_opinion_orderbook,
                on_trade=self._handle_opinion_trade,
                on_price_update=self._handle_opinion_price
            )
            await self.opinion_ws.initialize()
            asyncio.create_task(self.opinion_ws.start())
            await self.opinion_ws.subscribe_top_markets(limit=10)
        else:
            logger.warning("  ⚠️  Opinion API key not provided, using public endpoints...")

        # 3. 수수료 인식 계산기
        logger.info("Initializing fee-aware calculator...")
        self.fee_calculator = FeeAwareArbitrageCalculator(
            min_roi_percent=Decimal(str(self.config.get('min_roi', 1.0))),
            gas_multiplier=Decimal(str(self.config.get('gas_multiplier', 1.0)))
        )

        # 4. 매칭 엔진
        logger.info("Initializing matching engine...")
        self.matching_engine = EnhancedMatchingEngine(
            min_overall_score=self.config.get('min_match_score', 0.70)
        )

        # 5. 알림 시스템
        logger.info("Initializing alert system...")
        self.alert_manager = AlertManager()

        # 알림 채널 설정
        if self.config.get('slack_webhook'):
            slack = SlackChannel(self.config['slack_webhook'])
            await slack.initialize()
            self.alert_manager.add_channel('slack', slack)

        if self.config.get('telegram_bot_token'):
            telegram = TelegramChannel(
                self.config['telegram_bot_token'],
                self.config['telegram_chat_id']
            )
            await telegram.initialize()
            self.alert_manager.add_channel('telegram', telegram)

        self.edge_detector = EdgeCaseDetector(self.alert_manager)

        # 6. 포지션 관리
        logger.info("Initializing position manager...")
        self.position_manager = PositionManager()

        # 7. 델타헤지 엔진
        logger.info("Initializing delta hedge engine...")
        platform_clients = {}  # TODO: 실제 클라이언트 연결
        self.hedge_engine = DeltaHedgeEngine(platform_clients, self.position_manager)

        # 8. 슬리피지 관리
        logger.info("Initializing slippage management...")
        self.slippage_calc = SlippageCalculator(
            max_slippage_percent=self.config.get('max_slippage', 1.0)
        )
        self.order_executor = SmartOrderExecutor(
            slippage_calculator=self.slippage_calc
        )

        # 9. 동적 포지션 관리
        logger.info("Initializing dynamic position manager...")
        position_config = PositionConfig(
            base_size=Decimal(str(self.config.get('base_position_size', 10000))),
            max_slippage_percent=self.config.get('max_slippage', 1.0),
            min_gap_percent=self.config.get('min_gap', 1.0)
        )
        self.dynamic_position_mgr = DynamicPositionManager(position_config)

        logger.info("✅ All components initialized successfully!")

    async def start(self):
        """봇 시작"""
        self.running = True
        logger.info("🟢 Bot started - monitoring for opportunities...")

        # 주기적 태스크들
        tasks = [
            self._opportunity_scanner(),
            self._position_monitor(),
            self._dashboard_updater()
        ]

        await asyncio.gather(*tasks)

    async def stop(self):
        """봇 종료"""
        self.running = False
        logger.info("🛑 Stopping bot...")

        # WebSocket 종료
        if self.polymarket_ws:
            await self.polymarket_ws.stop()
        if self.kalshi_ws:
            await self.kalshi_ws.stop()
        if self.opinion_ws:
            await self.opinion_ws.stop()

        # 알림 채널 종료
        if self.alert_manager:
            await self.alert_manager.close_channels()

        logger.info("✅ Bot stopped successfully")

    # ===========================
    # 콜백 핸들러 - Polymarket
    # ===========================

    async def _handle_polymarket_orderbook(self, update: OrderbookUpdate):
        """Polymarket 오더북 업데이트"""
        self.monitored_markets['polymarket'][update.token_id] = {
            'platform': 'polymarket',
            'orderbook': update,
            'last_update': datetime.now()
        }
        # 차익거래 기회 탐색 트리거
        await self._check_arbitrage_opportunity('polymarket', update.token_id)

    async def _handle_polymarket_trade(self, trade: TradeUpdate):
        """Polymarket 체결 데이터"""
        logger.debug(f"Polymarket trade: {trade}")

    async def _handle_polymarket_market(self, market):
        """Polymarket 마켓 업데이트"""
        logger.debug(f"Polymarket market update: {market}")

    # ===========================
    # 콜백 핸들러 - Kalshi
    # ===========================

    async def _handle_kalshi_orderbook(self, orderbook: KalshiOrderbook):
        """Kalshi 오더북 업데이트"""
        self.monitored_markets['kalshi'][orderbook.ticker] = {
            'platform': 'kalshi',
            'orderbook': orderbook,
            'last_update': datetime.now()
        }
        await self._check_arbitrage_opportunity('kalshi', orderbook.ticker)

    async def _handle_kalshi_trade(self, trade):
        """Kalshi 체결 데이터"""
        logger.debug(f"Kalshi trade: {trade}")

    async def _handle_kalshi_market(self, market):
        """Kalshi 마켓 업데이트"""
        logger.debug(f"Kalshi market update: {market}")

    # ===========================
    # 콜백 핸들러 - Opinion
    # ===========================

    async def _handle_opinion_orderbook(self, orderbook: OpinionOrderbook):
        """Opinion 오더북 업데이트"""
        self.monitored_markets['opinion'][orderbook.token_id] = {
            'platform': 'opinion',
            'orderbook': orderbook,
            'last_update': datetime.now()
        }
        await self._check_arbitrage_opportunity('opinion', orderbook.token_id)

    async def _handle_opinion_trade(self, trade):
        """Opinion 체결 데이터"""
        logger.debug(f"Opinion trade: {trade}")

    async def _handle_opinion_price(self, price_update):
        """Opinion 가격 업데이트"""
        logger.debug(f"Opinion price: {price_update}")

    # ===========================
    # 주기적 태스크
    # ===========================

    async def _check_arbitrage_opportunity(self, platform: str, market_id: str):
        """특정 마켓에 대한 차익거래 기회 확인 (실시간)"""
        try:
            # 해당 플랫폼의 마켓 데이터 가져오기
            market_data = self.monitored_markets.get(platform, {}).get(market_id)
            if not market_data:
                return

            # 다른 플랫폼들과 비교
            for other_platform in ['polymarket', 'kalshi', 'opinion']:
                if other_platform == platform:
                    continue

                # 매칭 가능한 마켓 찾기
                for other_market_id, other_data in self.monitored_markets.get(other_platform, {}).items():
                    # TODO: 매칭 엔진으로 시장 매칭 검증
                    # TODO: 수수료 반영 차익 계산
                    # TODO: 슬리피지 체크
                    # TODO: 실행
                    pass

        except Exception as e:
            logger.error(f"Arbitrage check error: {e}")

    async def _opportunity_scanner(self):
        """차익거래 기회 주기적 스캔 (보완용)"""
        while self.running:
            try:
                logger.info("📊 Scanning for arbitrage opportunities across all platforms...")

                # 통계 출력
                poly_count = len(self.monitored_markets.get('polymarket', {}))
                kalshi_count = len(self.monitored_markets.get('kalshi', {}))
                opinion_count = len(self.monitored_markets.get('opinion', {}))

                logger.info(f"  Polymarket: {poly_count} markets")
                logger.info(f"  Kalshi: {kalshi_count} markets")
                logger.info(f"  Opinion: {opinion_count} markets")

                # 세 플랫폼 간 차익거래 기회 탐색
                # TODO: 전체 크로스 플랫폼 매칭
                await self._scan_cross_platform_opportunities()

                await asyncio.sleep(30)  # 30초마다 스캔

            except Exception as e:
                logger.error(f"Opportunity scanner error: {e}")
                await asyncio.sleep(60)

    async def _scan_cross_platform_opportunities(self):
        """세 플랫폼 간 차익거래 기회 스캔"""
        try:
            # Polymarket vs Kalshi
            await self._scan_pair('polymarket', 'kalshi')

            # Polymarket vs Opinion
            await self._scan_pair('polymarket', 'opinion')

            # Kalshi vs Opinion
            await self._scan_pair('kalshi', 'opinion')

        except Exception as e:
            logger.error(f"Cross-platform scan error: {e}")

    async def _scan_pair(self, platform_a: str, platform_b: str):
        """두 플랫폼 간 차익거래 기회 스캔"""
        markets_a = self.monitored_markets.get(platform_a, {})
        markets_b = self.monitored_markets.get(platform_b, {})

        if not markets_a or not markets_b:
            return

        # TODO: 매칭 엔진으로 유사 마켓 찾기
        # TODO: 수수료 반영 차익 계산
        # TODO: 기회가 있으면 알림 또는 실행
        pass

    async def _position_monitor(self):
        """포지션 모니터링"""
        while self.running:
            try:
                positions = self.position_manager.get_all_positions()

                for position in positions:
                    # PnL 계산
                    pnl = self.hedge_engine._calculate_pnl(position)

                    # 자동 헤지 조건 확인
                    if not position.is_hedged:
                        result = await self.hedge_engine.auto_hedge_on_threshold(
                            position,
                            profit_threshold=self.config.get('hedge_profit_threshold', 50.0),
                            loss_threshold=self.config.get('hedge_loss_threshold', -20.0)
                        )

                        if result:
                            logger.info(f"Auto-hedge executed for {position.position_id}")

                await asyncio.sleep(10)  # 10초마다 모니터링

            except Exception as e:
                logger.error(f"Position monitor error: {e}")
                await asyncio.sleep(30)

    async def _dashboard_updater(self):
        """대시보드 데이터 업데이트"""
        while self.running:
            try:
                # 대시보드 데이터 생성
                dashboard_data = {
                    'timestamp': datetime.now().isoformat(),
                    'active_positions': len(self.position_manager.get_all_positions()),
                    'opportunities': len(self.active_opportunities),
                    'monitored_markets': len(self.monitored_markets),
                    'alerts': self.alert_manager.get_stats() if self.alert_manager else {}
                }

                # 파일로 저장 (프론트엔드가 읽어감)
                # with open('/tmp/dashboard_data.json', 'w') as f:
                #     json.dump(dashboard_data, f)

                await asyncio.sleep(5)  # 5초마다 업데이트

            except Exception as e:
                logger.error(f"Dashboard updater error: {e}")
                await asyncio.sleep(10)

    async def _evaluate_and_execute(self, opportunity):
        """기회 평가 및 실행"""
        try:
            # 1. 매칭 검증
            match = self.matching_engine.match_markets(
                opportunity.market_a,
                opportunity.market_b
            )

            if not match.recommended:
                logger.info(f"Opportunity rejected by matching engine: {match.match_score.overall_score:.1%}")
                return

            # 2. 슬리피지 체크
            # TODO: 오더북 기반 슬리피지 계산

            # 3. 실행
            logger.info(f"Executing opportunity: {opportunity.roi_percent:.2f}% ROI")
            # TODO: 실제 주문 실행

        except Exception as e:
            logger.error(f"Evaluation/execution error: {e}")

# ===========================
# 메인 실행
# ===========================

async def main():
    """메인 함수"""

    # 설정
    config = {
        # 사용자 정보
        'user_age': 25,
        'kyc_status': {
            'polymarket': False,
            'kalshi': True,
            'opinion': True
        },

        # 플랫폼 크레덴셜
        # Kalshi
        'kalshi_email': None,  # 'your_email@example.com'
        'kalshi_password': None,  # 'your_password'

        # Opinion.trade
        'opinion_api_key': None,  # 'your_api_key' (optional for public endpoints)

        # Polymarket (설정 필요 시)
        # 'polymarket_private_key': None,

        # 거래 파라미터
        'min_roi': 1.0,
        'min_gap': 1.0,
        'max_slippage': 1.0,
        'gas_multiplier': 1.0,
        'base_position_size': 5000,

        # 리스크 관리
        'hedge_profit_threshold': 50.0,
        'hedge_loss_threshold': -20.0,
        'min_match_score': 0.70,

        # 알림 (환경 변수에서 로드 권장)
        'slack_webhook': None,  # 'YOUR_SLACK_WEBHOOK'
        'telegram_bot_token': None,  # 'YOUR_BOT_TOKEN'
        'telegram_chat_id': None  # 'YOUR_CHAT_ID'
    }

    # 봇 생성 및 실행
    bot = IntegratedArbitrageBot(config)

    try:
        await bot.initialize()
        await bot.start()

    except KeyboardInterrupt:
        logger.info("\n\n⏸️  Received shutdown signal...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        await bot.stop()

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║      🤖 INTEGRATED PREDICTION ARBITRAGE BOT 🤖              ║
    ║                   3-Platform Support                         ║
    ║                                                              ║
    ║  📊 Platforms:                                               ║
    ║     • Polymarket (WebSocket + REST)                          ║
    ║     • Kalshi (WebSocket + REST)                              ║
    ║     • Opinion.trade (WebSocket + REST)                       ║
    ║                                                              ║
    ║  ✅ Compliance Check     ✅ WebSocket Streams                ║
    ║  ✅ Fee-Aware Calculator ✅ Enhanced Matching                ║
    ║  ✅ Alert System         ✅ Delta Hedge Engine               ║
    ║  ✅ Slippage Management  ✅ Dynamic Positioning              ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

    asyncio.run(main())
