"""
Advanced Alert System
고급 알림 시스템 (슬리피지/부분체결/오라클 업데이트)
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
import json
import logging
from enum import Enum

logger = logging.getLogger(__name__)

# ===========================
# 알림 타입 및 우선순위
# ===========================

class AlertType(Enum):
    """알림 타입"""
    # 긴급 알림 (즉시 조치 필요)
    CRITICAL_SLIPPAGE = "critical_slippage"
    PARTIAL_FILL_FAILED = "partial_fill_failed"
    ORACLE_DISPUTE = "oracle_dispute"
    SYSTEM_FAILURE = "system_failure"

    # 중요 알림
    HIGH_SLIPPAGE = "high_slippage"
    PARTIAL_FILL_WARNING = "partial_fill_warning"
    ORACLE_UPDATE = "oracle_update"
    PRICE_DIVERGENCE = "price_divergence"
    RESOLUTION_MISMATCH = "resolution_mismatch"

    # 정보 알림
    OPPORTUNITY_FOUND = "opportunity_found"
    TRADE_EXECUTED = "trade_executed"
    POSITION_CLOSED = "position_closed"
    MARKET_UPDATE = "market_update"

class AlertPriority(Enum):
    """알림 우선순위"""
    CRITICAL = 1  # 즉시 조치
    HIGH = 2      # 15분 내
    MEDIUM = 3    # 1시간 내
    LOW = 4       # 참고용

# ===========================
# 데이터 모델
# ===========================

@dataclass
class Alert:
    """알림 객체"""
    alert_id: str
    alert_type: AlertType
    priority: AlertPriority
    title: str
    message: str
    timestamp: datetime
    data: Dict = field(default_factory=dict)
    channels: List[str] = field(default_factory=list)  # ['slack', 'telegram', 'email']
    action_required: bool = False
    action_url: Optional[str] = None
    acknowledged: bool = False

@dataclass
class SlippageAlert(Alert):
    """슬리피지 알림"""
    expected_slippage: Decimal = Decimal('0')
    actual_slippage: Decimal = Decimal('0')
    impact_on_profit: Decimal = Decimal('0')

@dataclass
class PartialFillAlert(Alert):
    """부분체결 알림"""
    target_size: Decimal = Decimal('0')
    filled_size: Decimal = Decimal('0')
    fill_percentage: Decimal = Decimal('0')
    unfilled_markets: List[str] = field(default_factory=list)

@dataclass
class OracleAlert(Alert):
    """오라클 업데이트 알림"""
    market_id: str = ""
    oracle_source: str = ""
    update_type: str = ""  # 'price_update', 'resolution', 'dispute'
    previous_value: Optional[str] = None
    new_value: Optional[str] = None

# ===========================
# 알림 채널 인터페이스
# ===========================

class AlertChannel:
    """알림 채널 베이스 클래스"""

    async def send(self, alert: Alert) -> bool:
        """
        알림 전송

        Returns:
            성공 여부
        """
        raise NotImplementedError

class SlackChannel(AlertChannel):
    """Slack 알림 채널"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.session = None

    async def initialize(self):
        """세션 초기화"""
        self.session = aiohttp.ClientSession()

    async def send(self, alert: Alert) -> bool:
        """Slack 메시지 전송"""
        try:
            # 우선순위에 따른 이모지
            emoji_map = {
                AlertPriority.CRITICAL: "🚨",
                AlertPriority.HIGH: "⚠️",
                AlertPriority.MEDIUM: "⚡",
                AlertPriority.LOW: "ℹ️"
            }
            emoji = emoji_map.get(alert.priority, "📢")

            # 메시지 구성
            message = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{emoji} {alert.title}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": alert.message
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Priority:* {alert.priority.name} | *Time:* {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                            }
                        ]
                    }
                ]
            }

            # 조치 버튼 추가
            if alert.action_required and alert.action_url:
                message["blocks"].append({
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Take Action"
                            },
                            "url": alert.action_url,
                            "style": "danger" if alert.priority == AlertPriority.CRITICAL else "primary"
                        }
                    ]
                })

            async with self.session.post(self.webhook_url, json=message) as response:
                if response.status == 200:
                    logger.info(f"Slack alert sent: {alert.alert_id}")
                    return True
                else:
                    logger.error(f"Slack alert failed: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Slack send error: {e}")
            return False

    async def close(self):
        """세션 종료"""
        if self.session:
            await self.session.close()

class TelegramChannel(AlertChannel):
    """Telegram 알림 채널"""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self.session = None

    async def initialize(self):
        """세션 초기화"""
        self.session = aiohttp.ClientSession()

    async def send(self, alert: Alert) -> bool:
        """Telegram 메시지 전송"""
        try:
            # 메시지 포맷팅
            priority_icon = {
                AlertPriority.CRITICAL: "🚨🚨🚨",
                AlertPriority.HIGH: "⚠️",
                AlertPriority.MEDIUM: "⚡",
                AlertPriority.LOW: "ℹ️"
            }

            text = f"{priority_icon.get(alert.priority, '📢')} *{alert.title}*\n\n"
            text += f"{alert.message}\n\n"
            text += f"_Priority: {alert.priority.name}_\n"
            text += f"_Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}_"

            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }

            async with self.session.post(self.api_url, json=payload) as response:
                if response.status == 200:
                    logger.info(f"Telegram alert sent: {alert.alert_id}")
                    return True
                else:
                    logger.error(f"Telegram alert failed: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False

    async def close(self):
        """세션 종료"""
        if self.session:
            await self.session.close()

class DiscordChannel(AlertChannel):
    """Discord 알림 채널"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.session = None

    async def initialize(self):
        """세션 초기화"""
        self.session = aiohttp.ClientSession()

    async def send(self, alert: Alert) -> bool:
        """Discord 메시지 전송"""
        try:
            # 우선순위별 색상
            color_map = {
                AlertPriority.CRITICAL: 0xFF0000,  # 빨강
                AlertPriority.HIGH: 0xFFA500,      # 주황
                AlertPriority.MEDIUM: 0xFFFF00,    # 노랑
                AlertPriority.LOW: 0x00FF00        # 초록
            }

            embed = {
                "title": alert.title,
                "description": alert.message,
                "color": color_map.get(alert.priority, 0x0000FF),
                "timestamp": alert.timestamp.isoformat(),
                "footer": {
                    "text": f"Priority: {alert.priority.name}"
                }
            }

            # 추가 필드
            if alert.data:
                fields = []
                for key, value in list(alert.data.items())[:5]:  # 최대 5개
                    fields.append({
                        "name": key.replace('_', ' ').title(),
                        "value": str(value),
                        "inline": True
                    })
                embed["fields"] = fields

            payload = {
                "embeds": [embed]
            }

            async with self.session.post(self.webhook_url, json=payload) as response:
                if response.status in [200, 204]:
                    logger.info(f"Discord alert sent: {alert.alert_id}")
                    return True
                else:
                    logger.error(f"Discord alert failed: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Discord send error: {e}")
            return False

    async def close(self):
        """세션 종료"""
        if self.session:
            await self.session.close()

class EmailChannel(AlertChannel):
    """이메일 알림 채널"""

    def __init__(self, smtp_config: Dict):
        """
        Args:
            smtp_config: {
                'host': 'smtp.gmail.com',
                'port': 587,
                'username': 'your@email.com',
                'password': 'app_password',
                'from': 'your@email.com',
                'to': ['recipient@email.com']
            }
        """
        self.config = smtp_config

    async def send(self, alert: Alert) -> bool:
        """이메일 전송 (간소화 버전)"""
        try:
            # 실제 구현은 aiosmtplib 등 사용
            logger.info(f"Email alert would be sent: {alert.alert_id}")
            # TODO: 실제 SMTP 전송 구현
            return True

        except Exception as e:
            logger.error(f"Email send error: {e}")
            return False

# ===========================
# 알림 관리자
# ===========================

class AlertManager:
    """알림 관리 시스템"""

    def __init__(self):
        self.channels: Dict[str, AlertChannel] = {}
        self.alert_history: List[Alert] = []
        self.alert_handlers: Dict[AlertType, List[Callable]] = {}

        # 통계
        self.stats = {
            'total_sent': 0,
            'by_type': {},
            'by_priority': {},
            'failed': 0
        }

    def add_channel(self, name: str, channel: AlertChannel):
        """알림 채널 추가"""
        self.channels[name] = channel
        logger.info(f"Alert channel added: {name}")

    def register_handler(self, alert_type: AlertType, handler: Callable):
        """알림 타입별 핸들러 등록"""
        if alert_type not in self.alert_handlers:
            self.alert_handlers[alert_type] = []
        self.alert_handlers[alert_type].append(handler)

    async def send_alert(
        self,
        alert: Alert,
        channels: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        알림 전송

        Args:
            alert: 알림 객체
            channels: 전송할 채널 리스트 (None이면 alert.channels 사용)

        Returns:
            채널별 전송 결과
        """

        # 채널 결정
        target_channels = channels or alert.channels or list(self.channels.keys())

        # 알림 기록
        self.alert_history.append(alert)

        # 핸들러 실행
        if alert.alert_type in self.alert_handlers:
            for handler in self.alert_handlers[alert.alert_type]:
                try:
                    await handler(alert)
                except Exception as e:
                    logger.error(f"Alert handler error: {e}")

        # 채널별 전송
        results = {}
        for channel_name in target_channels:
            channel = self.channels.get(channel_name)
            if channel:
                try:
                    success = await channel.send(alert)
                    results[channel_name] = success

                    if success:
                        self.stats['total_sent'] += 1
                    else:
                        self.stats['failed'] += 1

                except Exception as e:
                    logger.error(f"Channel {channel_name} error: {e}")
                    results[channel_name] = False
                    self.stats['failed'] += 1
            else:
                logger.warning(f"Channel not found: {channel_name}")
                results[channel_name] = False

        # 통계 업데이트
        alert_type_name = alert.alert_type.value
        self.stats['by_type'][alert_type_name] = self.stats['by_type'].get(alert_type_name, 0) + 1

        priority_name = alert.priority.name
        self.stats['by_priority'][priority_name] = self.stats['by_priority'].get(priority_name, 0) + 1

        return results

    async def initialize_channels(self):
        """모든 채널 초기화"""
        for channel in self.channels.values():
            if hasattr(channel, 'initialize'):
                await channel.initialize()

    async def close_channels(self):
        """모든 채널 종료"""
        for channel in self.channels.values():
            if hasattr(channel, 'close'):
                await channel.close()

    def get_stats(self) -> Dict:
        """통계 조회"""
        return {
            **self.stats,
            'recent_alerts': [
                {
                    'id': a.alert_id,
                    'type': a.alert_type.value,
                    'priority': a.priority.name,
                    'title': a.title,
                    'timestamp': a.timestamp.isoformat()
                }
                for a in self.alert_history[-10:]  # 최근 10개
            ]
        }

# ===========================
# 엣지 케이스 감지 시스템
# ===========================

class EdgeCaseDetector:
    """엣지 케이스 감지 및 알림"""

    def __init__(self, alert_manager: AlertManager):
        self.alert_manager = alert_manager

        # 임계값 설정
        self.thresholds = {
            'critical_slippage_percent': Decimal('2.0'),
            'high_slippage_percent': Decimal('1.0'),
            'min_fill_percentage': Decimal('80.0'),
            'oracle_update_delay_hours': 24,
            'price_divergence_percent': Decimal('5.0')
        }

    async def check_slippage(
        self,
        expected_slippage: Decimal,
        actual_slippage: Decimal,
        trade_data: Dict
    ):
        """슬리피지 체크"""

        slippage_diff = abs(actual_slippage - expected_slippage)

        if actual_slippage >= self.thresholds['critical_slippage_percent']:
            # 긴급: 2% 이상 슬리피지
            alert = SlippageAlert(
                alert_id=f"slippage_critical_{datetime.now().timestamp()}",
                alert_type=AlertType.CRITICAL_SLIPPAGE,
                priority=AlertPriority.CRITICAL,
                title="🚨 Critical Slippage Detected",
                message=f"Actual slippage ({actual_slippage}%) significantly exceeds threshold!\n"
                        f"Expected: {expected_slippage}%\n"
                        f"Market: {trade_data.get('market_id', 'Unknown')}\n"
                        f"Immediate review required.",
                timestamp=datetime.now(),
                expected_slippage=expected_slippage,
                actual_slippage=actual_slippage,
                impact_on_profit=trade_data.get('profit_impact', Decimal('0')),
                data=trade_data,
                channels=['slack', 'telegram'],
                action_required=True,
                action_url="http://dashboard/positions"
            )

        elif actual_slippage >= self.thresholds['high_slippage_percent']:
            # 경고: 1% 이상 슬리피지
            alert = SlippageAlert(
                alert_id=f"slippage_high_{datetime.now().timestamp()}",
                alert_type=AlertType.HIGH_SLIPPAGE,
                priority=AlertPriority.HIGH,
                title="⚠️ High Slippage Warning",
                message=f"Slippage higher than expected:\n"
                        f"Expected: {expected_slippage}%\n"
                        f"Actual: {actual_slippage}%\n"
                        f"Consider adjusting position sizes.",
                timestamp=datetime.now(),
                expected_slippage=expected_slippage,
                actual_slippage=actual_slippage,
                data=trade_data,
                channels=['slack']
            )

        else:
            # 정상 범위
            return

        await self.alert_manager.send_alert(alert)

    async def check_partial_fill(
        self,
        target_size: Decimal,
        filled_size: Decimal,
        unfilled_markets: List[str],
        trade_data: Dict
    ):
        """부분체결 체크"""

        fill_percentage = (filled_size / target_size * Decimal('100')) if target_size > 0 else Decimal('0')

        if fill_percentage < self.thresholds['min_fill_percentage']:
            # 80% 미만 체결
            alert = PartialFillAlert(
                alert_id=f"partial_fill_{datetime.now().timestamp()}",
                alert_type=AlertType.PARTIAL_FILL_WARNING,
                priority=AlertPriority.HIGH if fill_percentage < 50 else AlertPriority.MEDIUM,
                title=f"⚠️ Partial Fill: {fill_percentage:.1f}%",
                message=f"Order only {fill_percentage:.1f}% filled!\n"
                        f"Target: {target_size}\n"
                        f"Filled: {filled_size}\n"
                        f"Unfilled markets: {', '.join(unfilled_markets)}\n"
                        f"Consider hedging or canceling.",
                timestamp=datetime.now(),
                target_size=target_size,
                filled_size=filled_size,
                fill_percentage=fill_percentage,
                unfilled_markets=unfilled_markets,
                data=trade_data,
                channels=['slack', 'telegram'],
                action_required=True,
                action_url="http://dashboard/hedge"
            )

            await self.alert_manager.send_alert(alert)

    async def check_oracle_update(
        self,
        market_id: str,
        oracle_source: str,
        update_type: str,
        previous_value: Optional[str],
        new_value: Optional[str]
    ):
        """오라클 업데이트 감지"""

        # 업데이트 타입별 우선순위
        priority_map = {
            'dispute': AlertPriority.CRITICAL,
            'resolution': AlertPriority.HIGH,
            'price_update': AlertPriority.LOW
        }

        alert = OracleAlert(
            alert_id=f"oracle_{update_type}_{datetime.now().timestamp()}",
            alert_type=AlertType.ORACLE_UPDATE if update_type != 'dispute' else AlertType.ORACLE_DISPUTE,
            priority=priority_map.get(update_type, AlertPriority.MEDIUM),
            title=f"📡 Oracle {update_type.title()}: {oracle_source}",
            message=f"Oracle update detected:\n"
                    f"Market: {market_id}\n"
                    f"Source: {oracle_source}\n"
                    f"Type: {update_type}\n"
                    + (f"Previous: {previous_value}\n" if previous_value else "")
                    + (f"New: {new_value}" if new_value else ""),
            timestamp=datetime.now(),
            market_id=market_id,
            oracle_source=oracle_source,
            update_type=update_type,
            previous_value=previous_value,
            new_value=new_value,
            channels=['slack'],
            action_required=(update_type == 'dispute')
        )

        await self.alert_manager.send_alert(alert)

    async def check_price_divergence(
        self,
        market_a_price: Decimal,
        market_b_price: Decimal,
        market_pair: Tuple[str, str]
    ):
        """가격 괴리 체크"""

        avg_price = (market_a_price + market_b_price) / Decimal('2')
        divergence = abs(market_a_price - market_b_price) / avg_price * Decimal('100')

        if divergence >= self.thresholds['price_divergence_percent']:
            alert = Alert(
                alert_id=f"price_div_{datetime.now().timestamp()}",
                alert_type=AlertType.PRICE_DIVERGENCE,
                priority=AlertPriority.MEDIUM,
                title=f"⚡ Price Divergence: {divergence:.1f}%",
                message=f"Large price divergence detected:\n"
                        f"{market_pair[0]}: {market_a_price}\n"
                        f"{market_pair[1]}: {market_b_price}\n"
                        f"Divergence: {divergence:.1f}%\n"
                        f"Potential arbitrage or data error.",
                timestamp=datetime.now(),
                data={
                    'market_a': market_pair[0],
                    'market_b': market_pair[1],
                    'price_a': float(market_a_price),
                    'price_b': float(market_b_price),
                    'divergence_percent': float(divergence)
                },
                channels=['slack']
            )

            await self.alert_manager.send_alert(alert)

# ===========================
# 사용 예시
# ===========================

async def example_usage():
    """알림 시스템 사용 예시"""

    # 알림 관리자 생성
    alert_manager = AlertManager()

    # 채널 추가
    slack = SlackChannel(webhook_url="YOUR_SLACK_WEBHOOK_URL")
    telegram = TelegramChannel(bot_token="YOUR_BOT_TOKEN", chat_id="YOUR_CHAT_ID")
    discord = DiscordChannel(webhook_url="YOUR_DISCORD_WEBHOOK_URL")

    alert_manager.add_channel('slack', slack)
    alert_manager.add_channel('telegram', telegram)
    alert_manager.add_channel('discord', discord)

    # 채널 초기화
    await alert_manager.initialize_channels()

    # 엣지 케이스 감지기
    detector = EdgeCaseDetector(alert_manager)

    # 예시 1: 슬리피지 감지
    print("Testing slippage alert...")
    await detector.check_slippage(
        expected_slippage=Decimal('0.5'),
        actual_slippage=Decimal('2.5'),
        trade_data={
            'market_id': 'abc123',
            'platform': 'polymarket',
            'size': 10000,
            'profit_impact': Decimal('-150')
        }
    )

    await asyncio.sleep(1)

    # 예시 2: 부분체결 감지
    print("\nTesting partial fill alert...")
    await detector.check_partial_fill(
        target_size=Decimal('10000'),
        filled_size=Decimal('6500'),
        unfilled_markets=['kalshi_market_xyz'],
        trade_data={
            'opportunity_id': 'opp_456',
            'platforms': ['polymarket', 'kalshi']
        }
    )

    await asyncio.sleep(1)

    # 예시 3: 오라클 업데이트
    print("\nTesting oracle alert...")
    await detector.check_oracle_update(
        market_id='crypto_btc_100k',
        oracle_source='CoinMarketCap',
        update_type='dispute',
        previous_value='$95,000',
        new_value='$98,000'
    )

    # 통계 출력
    print("\n\n📊 Alert Statistics:")
    stats = alert_manager.get_stats()
    print(json.dumps(stats, indent=2, default=str))

    # 정리
    await alert_manager.close_channels()

if __name__ == "__main__":
    asyncio.run(example_usage())
