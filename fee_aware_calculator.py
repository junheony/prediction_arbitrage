"""
Fee-Aware Arbitrage Calculator
수수료 반영 차익거래 계산기 (p_yes + p_no + f < 1)
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal, getcontext
from datetime import datetime
import logging

# 고정밀 계산
getcontext().prec = 18

logger = logging.getLogger(__name__)

# ===========================
# 플랫폼별 수수료 정의
# ===========================

PLATFORM_FEES = {
    'polymarket': {
        'trading_fee_percent': Decimal('0'),  # 거래 수수료 없음
        'gas_fee_avg_usdc': Decimal('0.05'),  # 평균 가스비 (Polygon)
        'gas_fee_max_usdc': Decimal('0.20'),  # 최대 가스비 (혼잡 시)
        'withdrawal_fee_percent': Decimal('0'),
        'network': 'Polygon',
        'notes': 'Gas fees vary with network congestion'
    },
    'kalshi': {
        'trading_fee_percent': Decimal('0.70'),  # 0.7% 거래 수수료
        'withdrawal_fee_usd': Decimal('2.00'),  # 출금 수수료
        'max_fee_per_contract': Decimal('1.00'),  # 계약당 최대 수수료
        'network': 'Centralized',
        'notes': 'Fees capped at $1 per contract'
    },
    'manifold': {
        'trading_fee_percent': Decimal('0'),  # Play money는 수수료 없음
        'real_money_conversion_fee': Decimal('5.00'),  # 실제 기부 시 수수료
        'withdrawal_fee_percent': Decimal('0'),
        'network': 'Centralized',
        'notes': 'Play money platform, minimal real fees'
    }
}

# ===========================
# 데이터 모델
# ===========================

@dataclass
class FeeStructure:
    """수수료 구조"""
    platform: str
    trading_fee: Decimal  # 거래 수수료 (%)
    fixed_fee: Decimal  # 고정 수수료 (USDC/USD)
    gas_fee: Decimal  # 가스 수수료 (블록체인만)
    total_fee_percent: Decimal  # 총 수수료율
    total_fee_absolute: Decimal  # 절대 수수료 금액

@dataclass
class ArbitrageOpportunity:
    """수수료 반영 차익거래 기회"""
    market_a: Dict
    market_b: Dict
    position_a: str  # 'yes' or 'no'
    position_b: str  # 'yes' or 'no'

    # 가격 정보
    price_a: Decimal
    price_b: Decimal
    raw_cost: Decimal  # 순수 비용 (수수료 제외)

    # 수수료 정보
    fee_a: FeeStructure
    fee_b: FeeStructure
    total_fees: Decimal  # 총 수수료

    # 수익성 지표
    total_cost: Decimal  # 수수료 포함 총 비용
    expected_return: Decimal  # 예상 수익 (항상 1.0)
    gross_profit: Decimal  # 총 수익 (수수료 전)
    net_profit: Decimal  # 순 수익 (수수료 후)
    roi_percent: Decimal  # ROI (%)

    # 검증 플래그
    is_valid: bool  # p_yes + p_no + f < 1 조건 만족
    meets_min_roi: bool  # 최소 ROI 기준 충족

    # 메타 정보
    timestamp: datetime
    confidence_score: float

# ===========================
# 수수료 계산기
# ===========================

class FeeCalculator:
    """플랫폼별 수수료 계산"""

    @staticmethod
    def calculate_platform_fee(
        platform: str,
        position_size: Decimal,
        price: Decimal,
        gas_price_multiplier: Decimal = Decimal('1.0')
    ) -> FeeStructure:
        """
        플랫폼별 수수료 계산

        Args:
            platform: 플랫폼 이름
            position_size: 포지션 크기 (USDC/USD)
            price: 거래 가격
            gas_price_multiplier: 가스비 배수 (1.0 = 평균, 2.0 = 혼잡)
        """
        fee_config = PLATFORM_FEES.get(platform, {})

        # 거래 수수료 (퍼센트)
        trading_fee_percent = fee_config.get('trading_fee_percent', Decimal('0'))
        trading_fee = position_size * price * (trading_fee_percent / Decimal('100'))

        # 고정 수수료
        fixed_fee = Decimal('0')
        if 'withdrawal_fee_usd' in fee_config:
            # 출금 수수료는 총 거래 종료 시 1회만 발생하므로 분할
            fixed_fee = fee_config['withdrawal_fee_usd'] / Decimal('2')  # 양쪽 나누기

        # 가스비 (블록체인만)
        gas_fee = Decimal('0')
        if 'gas_fee_avg_usdc' in fee_config:
            avg_gas = fee_config['gas_fee_avg_usdc']
            gas_fee = avg_gas * gas_price_multiplier

            # 최대 가스비 제한
            max_gas = fee_config.get('gas_fee_max_usdc', avg_gas * Decimal('4'))
            gas_fee = min(gas_fee, max_gas)

        # Kalshi 수수료 캡 적용
        if platform == 'kalshi':
            max_fee_per_contract = fee_config.get('max_fee_per_contract', Decimal('1.0'))
            trading_fee = min(trading_fee, max_fee_per_contract)

        # 총 수수료
        total_fee_absolute = trading_fee + fixed_fee + gas_fee

        # 퍼센트로 환산
        invested_amount = position_size * price
        total_fee_percent = (total_fee_absolute / invested_amount * Decimal('100')) if invested_amount > 0 else Decimal('0')

        return FeeStructure(
            platform=platform,
            trading_fee=trading_fee,
            fixed_fee=fixed_fee,
            gas_fee=gas_fee,
            total_fee_percent=total_fee_percent,
            total_fee_absolute=total_fee_absolute
        )

# ===========================
# 차익거래 계산기
# ===========================

class FeeAwareArbitrageCalculator:
    """수수료 반영 차익거래 계산기"""

    def __init__(
        self,
        min_roi_percent: Decimal = Decimal('1.0'),
        max_total_fee_percent: Decimal = Decimal('2.0'),
        gas_multiplier: Decimal = Decimal('1.0')
    ):
        self.min_roi_percent = min_roi_percent
        self.max_total_fee_percent = max_total_fee_percent
        self.gas_multiplier = gas_multiplier
        self.fee_calculator = FeeCalculator()

    def calculate_opportunity(
        self,
        market_a: Dict,
        market_b: Dict,
        position_size: Decimal = Decimal('1000')
    ) -> Optional[ArbitrageOpportunity]:
        """
        차익거래 기회 계산 (수수료 반영)

        Args:
            market_a: 첫 번째 마켓 정보
                {
                    'platform': 'polymarket',
                    'market_id': 'xxx',
                    'question': 'Will...',
                    'yes_price': 0.65,
                    'no_price': 0.35
                }
            market_b: 두 번째 마켓 정보
            position_size: 포지션 크기 (기본 $1000)

        Returns:
            ArbitrageOpportunity or None
        """

        # 가능한 전략들 평가
        strategies = [
            ('yes', 'no'),  # A에서 YES, B에서 NO
            ('no', 'yes'),  # A에서 NO, B에서 YES
        ]

        best_opportunity = None
        best_roi = Decimal('-999999')

        for position_a, position_b in strategies:
            opportunity = self._evaluate_strategy(
                market_a, market_b,
                position_a, position_b,
                position_size
            )

            if opportunity and opportunity.is_valid:
                if opportunity.roi_percent > best_roi:
                    best_roi = opportunity.roi_percent
                    best_opportunity = opportunity

        return best_opportunity

    def _evaluate_strategy(
        self,
        market_a: Dict,
        market_b: Dict,
        position_a: str,
        position_b: str,
        position_size: Decimal
    ) -> Optional[ArbitrageOpportunity]:
        """특정 전략 평가"""

        try:
            # 가격 추출
            price_a = Decimal(str(market_a.get(f'{position_a}_price', 0)))
            price_b = Decimal(str(market_b.get(f'{position_b}_price', 0)))

            if price_a == 0 or price_b == 0:
                return None

            # 순수 비용 (수수료 제외)
            raw_cost = price_a + price_b

            # 플랫폼별 수수료 계산
            fee_a = self.fee_calculator.calculate_platform_fee(
                platform=market_a['platform'],
                position_size=position_size,
                price=price_a,
                gas_price_multiplier=self.gas_multiplier
            )

            fee_b = self.fee_calculator.calculate_platform_fee(
                platform=market_b['platform'],
                position_size=position_size,
                price=price_b,
                gas_price_multiplier=self.gas_multiplier
            )

            # 총 수수료
            total_fees = fee_a.total_fee_absolute + fee_b.total_fee_absolute

            # 총 비용 (수수료 포함)
            total_cost = (price_a + price_b) * position_size + total_fees

            # 예상 수익 (결과와 무관하게 1 USDC 보장)
            expected_return = position_size * Decimal('1.0')

            # 수익 계산
            gross_profit = expected_return - (price_a + price_b) * position_size
            net_profit = expected_return - total_cost

            # ROI
            roi_percent = (net_profit / total_cost * Decimal('100')) if total_cost > 0 else Decimal('0')

            # 검증: p_yes + p_no + f < 1
            total_fee_per_unit = total_fees / position_size
            is_valid = (price_a + price_b + total_fee_per_unit) < Decimal('1.0')

            # 최소 ROI 충족 여부
            meets_min_roi = roi_percent >= self.min_roi_percent

            # 신뢰도 점수 계산
            confidence_score = self._calculate_confidence(
                market_a, market_b, fee_a, fee_b, roi_percent
            )

            opportunity = ArbitrageOpportunity(
                market_a=market_a,
                market_b=market_b,
                position_a=position_a,
                position_b=position_b,
                price_a=price_a,
                price_b=price_b,
                raw_cost=raw_cost,
                fee_a=fee_a,
                fee_b=fee_b,
                total_fees=total_fees,
                total_cost=total_cost,
                expected_return=expected_return,
                gross_profit=gross_profit,
                net_profit=net_profit,
                roi_percent=roi_percent,
                is_valid=is_valid,
                meets_min_roi=meets_min_roi,
                timestamp=datetime.now(),
                confidence_score=confidence_score
            )

            return opportunity

        except Exception as e:
            logger.error(f"Error evaluating strategy: {e}")
            return None

    def _calculate_confidence(
        self,
        market_a: Dict,
        market_b: Dict,
        fee_a: FeeStructure,
        fee_b: FeeStructure,
        roi_percent: Decimal
    ) -> float:
        """신뢰도 점수 계산"""

        confidence = 1.0

        # ROI 기반 점수 (높을수록 좋음)
        roi_score = min(float(roi_percent) / 5.0, 1.0)  # 5% ROI = 만점
        confidence *= (0.5 + roi_score * 0.5)

        # 수수료 비율 점수 (낮을수록 좋음)
        avg_fee_percent = (fee_a.total_fee_percent + fee_b.total_fee_percent) / Decimal('2')
        fee_penalty = min(float(avg_fee_percent) / 2.0, 1.0)  # 2% 이상 = 최대 페널티
        confidence *= (1.0 - fee_penalty * 0.3)

        # 유동성 점수
        liquidity_a = float(market_a.get('liquidity', 0))
        liquidity_b = float(market_b.get('liquidity', 0))
        min_liquidity = min(liquidity_a, liquidity_b)

        if min_liquidity < 10000:
            confidence *= 0.7
        elif min_liquidity < 50000:
            confidence *= 0.85

        return max(0.0, min(confidence, 1.0))

    def find_opportunities_batch(
        self,
        markets: List[Dict],
        position_size: Decimal = Decimal('1000')
    ) -> List[ArbitrageOpportunity]:
        """
        여러 마켓에서 차익거래 기회 일괄 탐색

        Args:
            markets: 마켓 리스트
            position_size: 포지션 크기

        Returns:
            발견된 기회 리스트 (ROI 순 정렬)
        """
        opportunities = []

        # 모든 마켓 쌍 검사
        for i in range(len(markets)):
            for j in range(i + 1, len(markets)):
                market_a = markets[i]
                market_b = markets[j]

                # 같은 플랫폼끼리는 차익거래 불가
                if market_a['platform'] == market_b['platform']:
                    continue

                # 질문 유사도 체크 (간단한 버전)
                if not self._are_similar_markets(market_a, market_b):
                    continue

                # 기회 계산
                opportunity = self.calculate_opportunity(
                    market_a, market_b, position_size
                )

                if opportunity and opportunity.is_valid and opportunity.meets_min_roi:
                    opportunities.append(opportunity)

        # ROI 기준 정렬
        opportunities.sort(key=lambda x: x.roi_percent, reverse=True)

        return opportunities

    def _are_similar_markets(self, market_a: Dict, market_b: Dict) -> bool:
        """마켓 유사도 간단 체크"""
        # 실제로는 더 정교한 NLP 필요
        question_a = market_a.get('question', '').lower()
        question_b = market_b.get('question', '').lower()

        # 공통 단어 비율
        words_a = set(question_a.split())
        words_b = set(question_b.split())

        if not words_a or not words_b:
            return False

        intersection = words_a.intersection(words_b)
        union = words_a.union(words_b)

        similarity = len(intersection) / len(union)

        return similarity > 0.5  # 50% 이상 유사

    def print_opportunity(self, opp: ArbitrageOpportunity):
        """기회 정보 출력"""
        print("\n" + "="*70)
        print(f"🎯 ARBITRAGE OPPORTUNITY (ROI: {opp.roi_percent:.2f}%)")
        print("="*70)

        print(f"\n📊 Market A: {opp.market_a['platform'].upper()}")
        print(f"   Position: {opp.position_a.upper()} @ {opp.price_a:.4f}")
        print(f"   Fee: ${opp.fee_a.total_fee_absolute:.4f} ({opp.fee_a.total_fee_percent:.2f}%)")

        print(f"\n📊 Market B: {opp.market_b['platform'].upper()}")
        print(f"   Position: {opp.position_b.upper()} @ {opp.price_b:.4f}")
        print(f"   Fee: ${opp.fee_b.total_fee_absolute:.4f} ({opp.fee_b.total_fee_percent:.2f}%)")

        print(f"\n💰 Financial Analysis:")
        print(f"   Raw Cost: {opp.raw_cost:.4f}")
        print(f"   Total Fees: ${opp.total_fees:.4f}")
        print(f"   Total Cost: ${opp.total_cost:.2f}")
        print(f"   Expected Return: ${opp.expected_return:.2f}")
        print(f"   Gross Profit: ${opp.gross_profit:.2f}")
        print(f"   Net Profit: ${opp.net_profit:.2f}")
        print(f"   ROI: {opp.roi_percent:.2f}%")

        print(f"\n✅ Validation:")
        print(f"   p_yes + p_no + f < 1: {'PASS' if opp.is_valid else 'FAIL'}")
        print(f"   Meets Min ROI: {'PASS' if opp.meets_min_roi else 'FAIL'}")
        print(f"   Confidence: {opp.confidence_score:.2%}")

        print("="*70 + "\n")

# ===========================
# 사용 예시
# ===========================

async def example_usage():
    """수수료 반영 계산기 사용 예시"""

    # 계산기 생성 (최소 ROI 1%)
    calculator = FeeAwareArbitrageCalculator(
        min_roi_percent=Decimal('1.0'),
        gas_multiplier=Decimal('1.0')  # 평균 가스비
    )

    # 샘플 마켓 데이터
    market_polymarket = {
        'platform': 'polymarket',
        'market_id': 'abc123',
        'question': 'Will BTC reach $100k by 2025?',
        'yes_price': 0.65,
        'no_price': 0.35,
        'liquidity': 500000,
        'volume': 1000000
    }

    market_kalshi = {
        'platform': 'kalshi',
        'market_id': 'xyz789',
        'question': 'Bitcoin above $100k by end of 2025?',
        'yes_price': 0.30,
        'no_price': 0.70,
        'liquidity': 300000,
        'volume': 500000
    }

    # 차익거래 기회 계산
    print("🔍 Calculating arbitrage opportunity...\n")
    opportunity = calculator.calculate_opportunity(
        market_polymarket,
        market_kalshi,
        position_size=Decimal('1000')
    )

    if opportunity:
        calculator.print_opportunity(opportunity)

        # 시뮬레이션: 다양한 포지션 크기 테스트
        print("\n📈 Position Size Analysis:")
        print(f"{'Size':<10} {'Net Profit':<12} {'ROI':<8} {'Total Fees':<12}")
        print("-" * 50)

        for size in [100, 500, 1000, 5000, 10000]:
            opp = calculator.calculate_opportunity(
                market_polymarket,
                market_kalshi,
                position_size=Decimal(str(size))
            )
            if opp:
                print(f"${size:<9} ${float(opp.net_profit):<11.2f} {float(opp.roi_percent):<7.2f}% ${float(opp.total_fees):<11.2f}")

    else:
        print("❌ No valid arbitrage opportunity found")

    # 배치 탐색 예시
    print("\n\n🔎 Batch Search Example:")
    markets = [market_polymarket, market_kalshi]
    opportunities = calculator.find_opportunities_batch(markets)

    print(f"Found {len(opportunities)} opportunities")
    for opp in opportunities[:3]:  # 상위 3개만
        print(f"  - {opp.market_a['platform']} ↔️ {opp.market_b['platform']}: ROI {opp.roi_percent:.2f}%")

if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())
