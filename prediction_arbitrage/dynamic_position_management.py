"""
Dynamic Position Management & Advanced Risk Control System
동적 포지션 관리 및 고급 리스크 제어 시스템
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from decimal import Decimal
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
import json

@dataclass
class PositionConfig:
    """포지션 설정"""
    # 기본 설정
    base_size: Decimal = Decimal(10000)
    min_size: Decimal = Decimal(100)
    max_size: Decimal = Decimal(50000)
    
    # 슬리피지 설정
    max_slippage_percent: float = 1.0
    slippage_adjustment_factor: float = 0.8  # 슬리피지당 크기 감소율
    
    # 갭 설정
    min_gap_percent: float = 1.0  # 최소 가격 차이
    optimal_gap_percent: float = 3.0  # 최적 가격 차이
    
    # 분할 설정
    enable_split_orders: bool = True
    max_splits: int = 10
    split_delay_ms: int = 1000
    
    # 리스크 설정
    max_correlation: float = 0.7  # 최대 상관관계
    max_single_market_exposure: Decimal = Decimal(20000)
    max_total_exposure: Decimal = Decimal(100000)

@dataclass
class MarketConditions:
    """시장 상황 데이터"""
    volatility: float
    liquidity_score: float
    spread_percentage: float
    recent_volume: Decimal
    price_trend: str  # 'up', 'down', 'stable'
    confidence_level: float

# ===========================
# 동적 포지션 매니저
# ===========================

class DynamicPositionManager:
    """시장 상황에 따른 동적 포지션 관리"""
    
    def __init__(self, config: PositionConfig):
        self.config = config
        self.active_positions = {}
        self.position_history = []
        self.market_conditions_cache = {}
        
    def calculate_dynamic_position_size(
        self,
        base_opportunity: Dict,
        market_conditions: MarketConditions,
        current_exposure: Decimal,
        orderbook_depth: Dict
    ) -> Dict:
        """
        동적 포지션 크기 계산
        
        Returns:
            Dict containing:
            - recommended_size: 권장 포지션 크기
            - split_strategy: 분할 전략
            - confidence: 신뢰도
            - adjustments: 적용된 조정 사항
        """
        
        adjustments = []
        size = self.config.base_size
        
        # 1. 가격 갭에 따른 조정
        gap_adjustment = self._adjust_for_price_gap(
            base_opportunity['price_gap_percent']
        )
        size = size * Decimal(str(gap_adjustment['multiplier']))
        adjustments.append(f"Price gap adjustment: {gap_adjustment['multiplier']:.2f}x")
        
        # 2. 유동성에 따른 조정
        liquidity_adjustment = self._adjust_for_liquidity(
            orderbook_depth,
            market_conditions.liquidity_score
        )
        size = size * Decimal(str(liquidity_adjustment['multiplier']))
        adjustments.append(f"Liquidity adjustment: {liquidity_adjustment['multiplier']:.2f}x")
        
        # 3. 변동성에 따른 조정
        volatility_adjustment = self._adjust_for_volatility(
            market_conditions.volatility
        )
        size = size * Decimal(str(volatility_adjustment['multiplier']))
        adjustments.append(f"Volatility adjustment: {volatility_adjustment['multiplier']:.2f}x")
        
        # 4. 현재 노출도에 따른 조정
        exposure_adjustment = self._adjust_for_exposure(
            current_exposure,
            self.config.max_total_exposure
        )
        size = size * Decimal(str(exposure_adjustment['multiplier']))
        adjustments.append(f"Exposure adjustment: {exposure_adjustment['multiplier']:.2f}x")
        
        # 5. 슬리피지 예상에 따른 조정
        slippage_estimate = self._estimate_slippage(size, orderbook_depth)
        if slippage_estimate > self.config.max_slippage_percent:
            # 슬리피지가 크면 크기 감소
            reduction_factor = self.config.max_slippage_percent / slippage_estimate
            size = size * Decimal(str(reduction_factor * self.config.slippage_adjustment_factor))
            adjustments.append(f"Slippage reduction: {reduction_factor:.2f}x")
        
        # 크기 제한 적용
        size = max(self.config.min_size, min(size, self.config.max_size))
        
        # 분할 전략 결정
        split_strategy = self._determine_split_strategy(
            size,
            slippage_estimate,
            orderbook_depth,
            market_conditions
        )
        
        # 신뢰도 계산
        confidence = self._calculate_position_confidence(
            gap_adjustment['score'],
            liquidity_adjustment['score'],
            volatility_adjustment['score'],
            exposure_adjustment['score'],
            slippage_estimate
        )
        
        return {
            'recommended_size': size,
            'split_strategy': split_strategy,
            'confidence': confidence,
            'adjustments': adjustments,
            'estimated_slippage': slippage_estimate,
            'risk_score': self._calculate_risk_score(
                size, market_conditions, current_exposure
            )
        }
    
    def _adjust_for_price_gap(self, gap_percent: float) -> Dict:
        """가격 차이에 따른 크기 조정"""
        
        if gap_percent < self.config.min_gap_percent:
            # 갭이 너무 작으면 진입 안함
            return {'multiplier': 0, 'score': 0}
        
        if gap_percent >= self.config.optimal_gap_percent:
            # 최적 갭 이상이면 크기 증가
            multiplier = min(2.0, 1.0 + (gap_percent - self.config.optimal_gap_percent) * 0.2)
            score = 1.0
        else:
            # 최소~최적 사이는 선형 조정
            ratio = (gap_percent - self.config.min_gap_percent) / (
                self.config.optimal_gap_percent - self.config.min_gap_percent
            )
            multiplier = 0.5 + ratio * 0.5
            score = ratio
        
        return {'multiplier': multiplier, 'score': score}
    
    def _adjust_for_liquidity(
        self,
        orderbook_depth: Dict,
        liquidity_score: float
    ) -> Dict:
        """유동성에 따른 크기 조정"""
        
        # 오더북 깊이 분석
        total_depth = sum(
            Decimal(str(level['size']))
            for levels in orderbook_depth.values()
            for level in levels[:10]
        )
        
        # 유동성 점수와 오더북 깊이 종합
        if liquidity_score > 0.8 and total_depth > Decimal(100000):
            multiplier = 1.5  # 유동성 좋으면 크기 증가
            score = 1.0
        elif liquidity_score > 0.5 and total_depth > Decimal(50000):
            multiplier = 1.0
            score = 0.7
        elif liquidity_score > 0.3 and total_depth > Decimal(10000):
            multiplier = 0.7
            score = 0.5
        else:
            multiplier = 0.3  # 유동성 나쁘면 크기 감소
            score = 0.2
        
        return {'multiplier': multiplier, 'score': score}
    
    def _adjust_for_volatility(self, volatility: float) -> Dict:
        """변동성에 따른 크기 조정"""
        
        # 높은 변동성 = 작은 포지션
        if volatility < 0.1:  # 낮은 변동성
            multiplier = 1.2
            score = 0.9
        elif volatility < 0.3:  # 보통 변동성
            multiplier = 1.0
            score = 0.7
        elif volatility < 0.5:  # 높은 변동성
            multiplier = 0.7
            score = 0.5
        else:  # 매우 높은 변동성
            multiplier = 0.4
            score = 0.2
        
        return {'multiplier': multiplier, 'score': score}
    
    def _adjust_for_exposure(
        self,
        current_exposure: Decimal,
        max_exposure: Decimal
    ) -> Dict:
        """현재 노출도에 따른 크기 조정"""
        
        exposure_ratio = float(current_exposure / max_exposure)
        
        if exposure_ratio < 0.3:
            multiplier = 1.2  # 노출도 낮으면 크기 증가 가능
            score = 1.0
        elif exposure_ratio < 0.6:
            multiplier = 1.0
            score = 0.8
        elif exposure_ratio < 0.8:
            multiplier = 0.6
            score = 0.5
        else:
            multiplier = 0.2  # 노출도 높으면 크기 대폭 감소
            score = 0.2
        
        return {'multiplier': multiplier, 'score': score}
    
    def _estimate_slippage(
        self,
        size: Decimal,
        orderbook_depth: Dict
    ) -> float:
        """예상 슬리피지 계산"""
        
        if not orderbook_depth:
            return 5.0  # 오더북 없으면 최대 슬리피지 가정
        
        cumulative_size = Decimal(0)
        cumulative_cost = Decimal(0)
        levels = orderbook_depth.get('asks', []) + orderbook_depth.get('bids', [])
        
        if not levels:
            return 5.0
        
        best_price = Decimal(str(levels[0]['price']))
        
        for level in levels:
            level_size = Decimal(str(level['size']))
            level_price = Decimal(str(level['price']))
            
            if cumulative_size >= size:
                break
            
            fill_size = min(level_size, size - cumulative_size)
            cumulative_size += fill_size
            cumulative_cost += fill_size * level_price
        
        if cumulative_size == 0:
            return 5.0
        
        avg_price = cumulative_cost / cumulative_size
        slippage = abs(float((avg_price - best_price) / best_price * 100))
        
        return slippage
    
    def _determine_split_strategy(
        self,
        total_size: Decimal,
        estimated_slippage: float,
        orderbook_depth: Dict,
        market_conditions: MarketConditions
    ) -> Dict:
        """분할 주문 전략 결정"""
        
        if not self.config.enable_split_orders:
            return {
                'enabled': False,
                'num_splits': 1,
                'orders': [{'size': total_size, 'delay_ms': 0}]
            }
        
        # 슬리피지가 크거나 변동성이 높으면 분할
        should_split = (
            estimated_slippage > self.config.max_slippage_percent or
            market_conditions.volatility > 0.3
        )
        
        if not should_split:
            return {
                'enabled': False,
                'num_splits': 1,
                'orders': [{'size': total_size, 'delay_ms': 0}]
            }
        
        # 분할 수 계산
        num_splits = min(
            self.config.max_splits,
            max(2, int(estimated_slippage / self.config.max_slippage_percent) + 1)
        )
        
        # 분할 크기 (지수적 감소)
        split_sizes = self._calculate_exponential_splits(total_size, num_splits)
        
        orders = []
        for i, size in enumerate(split_sizes):
            orders.append({
                'size': size,
                'delay_ms': i * self.config.split_delay_ms,
                'type': 'market' if i == 0 else 'limit',
                'price_offset': i * 0.001  # 점진적 가격 오프셋
            })
        
        return {
            'enabled': True,
            'num_splits': num_splits,
            'orders': orders,
            'strategy': 'exponential_decay'
        }
    
    def _calculate_exponential_splits(
        self,
        total_size: Decimal,
        num_splits: int
    ) -> List[Decimal]:
        """지수적 감소 분할 크기 계산"""
        
        # 첫 주문이 가장 크고 점차 감소
        decay_factor = 0.7
        splits = []
        
        # 기하급수 합 공식으로 첫 항 계산
        first_size = total_size * (1 - decay_factor) / (1 - decay_factor ** num_splits)
        
        for i in range(num_splits):
            size = first_size * (decay_factor ** i)
            splits.append(size)
        
        # 합계 조정 (반올림 오차 보정)
        total_split = sum(splits)
        if total_split != total_size:
            adjustment = total_size - total_split
            splits[-1] += adjustment
        
        return splits
    
    def _calculate_position_confidence(
        self,
        gap_score: float,
        liquidity_score: float,
        volatility_score: float,
        exposure_score: float,
        slippage: float
    ) -> float:
        """포지션 신뢰도 종합 계산"""
        
        # 각 요소별 가중치
        weights = {
            'gap': 0.3,
            'liquidity': 0.25,
            'volatility': 0.2,
            'exposure': 0.15,
            'slippage': 0.1
        }
        
        # 슬리피지 점수 (낮을수록 좋음)
        slippage_score = max(0, 1.0 - (slippage / 5.0))
        
        # 가중 평균
        confidence = (
            gap_score * weights['gap'] +
            liquidity_score * weights['liquidity'] +
            volatility_score * weights['volatility'] +
            exposure_score * weights['exposure'] +
            slippage_score * weights['slippage']
        )
        
        return min(max(confidence, 0), 1.0)
    
    def _calculate_risk_score(
        self,
        position_size: Decimal,
        market_conditions: MarketConditions,
        current_exposure: Decimal
    ) -> float:
        """리스크 점수 계산 (0=안전, 1=위험)"""
        
        risk_factors = []
        
        # 크기 리스크
        size_ratio = float(position_size / self.config.max_size)
        risk_factors.append(size_ratio * 0.3)
        
        # 변동성 리스크
        risk_factors.append(market_conditions.volatility * 0.3)
        
        # 노출도 리스크
        exposure_ratio = float(current_exposure / self.config.max_total_exposure)
        risk_factors.append(exposure_ratio * 0.2)
        
        # 유동성 리스크 (낮을수록 위험)
        liquidity_risk = 1.0 - market_conditions.liquidity_score
        risk_factors.append(liquidity_risk * 0.2)
        
        return min(sum(risk_factors), 1.0)

# ===========================
# 고급 리스크 제어 시스템
# ===========================

class AdvancedRiskController:
    """고급 리스크 제어 및 모니터링"""
    
    def __init__(
        self,
        max_daily_loss: Decimal = Decimal(5000),
        max_position_correlation: float = 0.7,
        var_confidence_level: float = 0.95
    ):
        self.max_daily_loss = max_daily_loss
        self.max_position_correlation = max_position_correlation
        self.var_confidence_level = var_confidence_level
        
        self.daily_pnl = Decimal(0)
        self.position_correlations = defaultdict(float)
        self.risk_metrics = {}
        self.alerts = []
        
    def evaluate_position_entry(
        self,
        new_position: Dict,
        existing_positions: List[Dict],
        market_data: Dict
    ) -> Tuple[bool, str, Dict]:
        """
        새 포지션 진입 가능 여부 평가
        
        Returns:
            Tuple of (allowed, reason, risk_metrics)
        """
        
        risk_checks = []
        
        # 1. 일일 손실 한도 체크
        daily_loss_check = self._check_daily_loss_limit()
        risk_checks.append(daily_loss_check)
        
        # 2. 포지션 상관관계 체크
        correlation_check = self._check_position_correlation(
            new_position, existing_positions
        )
        risk_checks.append(correlation_check)
        
        # 3. VaR 한도 체크
        var_check = self._check_var_limit(
            new_position, existing_positions, market_data
        )
        risk_checks.append(var_check)
        
        # 4. 집중도 체크
        concentration_check = self._check_concentration_risk(
            new_position, existing_positions
        )
        risk_checks.append(concentration_check)
        
        # 5. 시장 상황 체크
        market_check = self._check_market_conditions(market_data)
        risk_checks.append(market_check)
        
        # 모든 체크 통과 여부
        all_passed = all(check['passed'] for check in risk_checks)
        
        # 실패 이유 수집
        failed_reasons = [
            check['reason'] for check in risk_checks if not check['passed']
        ]
        
        # 리스크 메트릭 계산
        risk_metrics = self._calculate_comprehensive_risk_metrics(
            new_position, existing_positions, risk_checks
        )
        
        if all_passed:
            return True, "All risk checks passed", risk_metrics
        else:
            return False, " | ".join(failed_reasons), risk_metrics
    
    def _check_daily_loss_limit(self) -> Dict:
        """일일 손실 한도 체크"""
        
        if abs(self.daily_pnl) >= self.max_daily_loss:
            return {
                'passed': False,
                'reason': f"Daily loss limit reached: {self.daily_pnl}",
                'metric': 'daily_loss'
            }
        
        remaining = self.max_daily_loss - abs(self.daily_pnl)
        return {
            'passed': True,
            'reason': f"Daily loss within limit. Remaining: {remaining}",
            'metric': 'daily_loss'
        }
    
    def _check_position_correlation(
        self,
        new_position: Dict,
        existing_positions: List[Dict]
    ) -> Dict:
        """포지션 간 상관관계 체크"""
        
        for position in existing_positions:
            correlation = self._calculate_correlation(new_position, position)
            
            if correlation > self.max_position_correlation:
                return {
                    'passed': False,
                    'reason': f"High correlation ({correlation:.2f}) with existing position",
                    'metric': 'correlation'
                }
        
        return {
            'passed': True,
            'reason': "Correlation within acceptable range",
            'metric': 'correlation'
        }
    
    def _check_var_limit(
        self,
        new_position: Dict,
        existing_positions: List[Dict],
        market_data: Dict
    ) -> Dict:
        """Value at Risk 한도 체크"""
        
        # 새 포지션 포함한 포트폴리오 VaR 계산
        portfolio = existing_positions + [new_position]
        portfolio_var = self._calculate_portfolio_var(portfolio, market_data)
        
        # VaR 한도 (총 자본의 5%)
        var_limit = Decimal(100000) * Decimal('0.05')
        
        if portfolio_var > var_limit:
            return {
                'passed': False,
                'reason': f"Portfolio VaR ({portfolio_var}) exceeds limit ({var_limit})",
                'metric': 'var'
            }
        
        return {
            'passed': True,
            'reason': f"Portfolio VaR within limit: {portfolio_var}",
            'metric': 'var'
        }
    
    def _check_concentration_risk(
        self,
        new_position: Dict,
        existing_positions: List[Dict]
    ) -> Dict:
        """집중도 리스크 체크"""
        
        # 플랫폼별 노출도 계산
        platform_exposure = defaultdict(Decimal)
        
        for pos in existing_positions:
            platform_exposure[pos['platform']] += pos['size']
        
        platform_exposure[new_position['platform']] += new_position['size']
        
        # 단일 플랫폼 최대 노출도 (총 노출도의 40%)
        total_exposure = sum(platform_exposure.values())
        max_platform_exposure = total_exposure * Decimal('0.4')
        
        for platform, exposure in platform_exposure.items():
            if exposure > max_platform_exposure:
                return {
                    'passed': False,
                    'reason': f"Platform concentration too high: {platform} = {exposure}",
                    'metric': 'concentration'
                }
        
        return {
            'passed': True,
            'reason': "Concentration risk acceptable",
            'metric': 'concentration'
        }
    
    def _check_market_conditions(self, market_data: Dict) -> Dict:
        """시장 상황 체크"""
        
        # 극단적 시장 상황 감지
        if market_data.get('volatility', 0) > 0.8:
            return {
                'passed': False,
                'reason': "Market volatility too high",
                'metric': 'market_conditions'
            }
        
        if market_data.get('liquidity_score', 1) < 0.2:
            return {
                'passed': False,
                'reason': "Market liquidity too low",
                'metric': 'market_conditions'
            }
        
        return {
            'passed': True,
            'reason': "Market conditions acceptable",
            'metric': 'market_conditions'
        }
    
    def _calculate_correlation(
        self,
        position1: Dict,
        position2: Dict
    ) -> float:
        """두 포지션 간 상관관계 계산"""
        
        # 간단한 규칙 기반 상관관계
        # 실제로는 과거 가격 데이터로 계산
        
        # 같은 플랫폼 = 높은 상관관계
        if position1['platform'] == position2['platform']:
            correlation = 0.6
        else:
            correlation = 0.2
        
        # 같은 카테고리 = 상관관계 증가
        if position1.get('category') == position2.get('category'):
            correlation += 0.2
        
        # 반대 방향 = 음의 상관관계
        if position1['side'] != position2['side']:
            correlation *= -0.5
        
        return min(max(correlation, -1), 1)
    
    def _calculate_portfolio_var(
        self,
        portfolio: List[Dict],
        market_data: Dict
    ) -> Decimal:
        """포트폴리오 VaR 계산"""
        
        if not portfolio:
            return Decimal(0)
        
        # Monte Carlo 시뮬레이션 (간소화)
        num_simulations = 1000
        portfolio_returns = []
        
        for _ in range(num_simulations):
            daily_return = 0
            
            for position in portfolio:
                # 포지션별 수익률 시뮬레이션
                volatility = market_data.get('volatility', 0.2)
                position_return = np.random.normal(0, volatility) * float(position['size'])
                daily_return += position_return
            
            portfolio_returns.append(daily_return)
        
        # VaR 계산 (95% 신뢰수준)
        var_percentile = (1 - self.var_confidence_level) * 100
        var = -np.percentile(portfolio_returns, var_percentile)
        
        return Decimal(str(var))
    
    def _calculate_comprehensive_risk_metrics(
        self,
        new_position: Dict,
        existing_positions: List[Dict],
        risk_checks: List[Dict]
    ) -> Dict:
        """종합 리스크 메트릭 계산"""
        
        # 리스크 점수 집계
        risk_scores = {
            'daily_loss': 0,
            'correlation': 0,
            'var': 0,
            'concentration': 0,
            'market_conditions': 0
        }
        
        for check in risk_checks:
            metric = check['metric']
            # 통과 = 0, 실패 = 1
            risk_scores[metric] = 0 if check['passed'] else 1
        
        # 전체 리스크 점수 (가중 평균)
        weights = {
            'daily_loss': 0.3,
            'correlation': 0.2,
            'var': 0.25,
            'concentration': 0.15,
            'market_conditions': 0.1
        }
        
        total_risk_score = sum(
            risk_scores[metric] * weight
            for metric, weight in weights.items()
        )
        
        return {
            'individual_scores': risk_scores,
            'total_risk_score': total_risk_score,
            'risk_level': self._get_risk_level(total_risk_score),
            'recommendations': self._get_risk_recommendations(risk_scores)
        }
    
    def _get_risk_level(self, score: float) -> str:
        """리스크 수준 결정"""
        if score < 0.2:
            return "LOW"
        elif score < 0.5:
            return "MEDIUM"
        elif score < 0.8:
            return "HIGH"
        else:
            return "CRITICAL"
    
    def _get_risk_recommendations(self, risk_scores: Dict) -> List[str]:
        """리스크 기반 권장사항"""
        
        recommendations = []
        
        if risk_scores['daily_loss'] > 0:
            recommendations.append("Consider reducing position size due to daily loss limit")
        
        if risk_scores['correlation'] > 0:
            recommendations.append("Diversify into uncorrelated markets")
        
        if risk_scores['var'] > 0:
            recommendations.append("Reduce overall portfolio exposure")
        
        if risk_scores['concentration'] > 0:
            recommendations.append("Spread positions across different platforms")
        
        if risk_scores['market_conditions'] > 0:
            recommendations.append("Wait for better market conditions")
        
        return recommendations

# ===========================
# 실시간 모니터링 시스템
# ===========================

class RealTimeMonitor:
    """실시간 포지션 및 리스크 모니터링"""
    
    def __init__(self):
        self.monitors = {}
        self.alerts = []
        self.metrics_history = defaultdict(list)
        
    async def monitor_positions(
        self,
        positions: List[Dict],
        market_data_stream
    ):
        """실시간 포지션 모니터링"""
        
        while True:
            try:
                # 시장 데이터 수신
                market_data = await market_data_stream.get()
                
                for position in positions:
                    # 포지션별 P&L 계산
                    pnl = self._calculate_real_time_pnl(position, market_data)
                    
                    # 알림 조건 체크
                    await self._check_alert_conditions(position, pnl, market_data)
                    
                    # 메트릭 기록
                    self._record_metrics(position, pnl, market_data)
                
                # 대시보드 업데이트
                await self._update_dashboard()
                
                await asyncio.sleep(1)  # 1초마다 업데이트
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                await asyncio.sleep(5)
    
    def _calculate_real_time_pnl(
        self,
        position: Dict,
        market_data: Dict
    ) -> Decimal:
        """실시간 손익 계산"""
        
        current_price = market_data.get(position['market_id'], {}).get('price', 0)
        entry_price = position['entry_price']
        size = position['size']
        
        if position['side'] == 'buy':
            pnl = (Decimal(str(current_price)) - entry_price) * size
        else:
            pnl = (entry_price - Decimal(str(current_price))) * size
        
        return pnl
    
    async def _check_alert_conditions(
        self,
        position: Dict,
        pnl: Decimal,
        market_data: Dict
    ):
        """알림 조건 확인"""
        
        # 손실 알림
        if pnl < -position['stop_loss']:
            await self._send_alert(
                f"STOP LOSS: Position {position['id']} reached stop loss: {pnl}"
            )
        
        # 수익 목표 달성
        elif pnl > position['take_profit']:
            await self._send_alert(
                f"TAKE PROFIT: Position {position['id']} reached target: {pnl}"
            )
        
        # 급격한 가격 변동
        volatility = market_data.get('volatility', 0)
        if volatility > 0.7:
            await self._send_alert(
                f"HIGH VOLATILITY: Market {position['market_id']} volatility: {volatility}"
            )
    
    async def _send_alert(self, message: str):
        """알림 전송"""
        
        alert = {
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'type': 'risk_alert'
        }
        
        self.alerts.append(alert)
        
        # 여기에 실제 알림 전송 로직 추가
        # (Slack, Telegram, Email 등)
        print(f"ALERT: {message}")
    
    def _record_metrics(
        self,
        position: Dict,
        pnl: Decimal,
        market_data: Dict
    ):
        """메트릭 기록"""
        
        metric = {
            'timestamp': datetime.now(),
            'position_id': position['id'],
            'pnl': float(pnl),
            'market_price': market_data.get(position['market_id'], {}).get('price', 0),
            'volatility': market_data.get('volatility', 0)
        }
        
        self.metrics_history[position['id']].append(metric)
        
        # 오래된 데이터 정리 (최근 1시간)
        cutoff_time = datetime.now() - timedelta(hours=1)
        self.metrics_history[position['id']] = [
            m for m in self.metrics_history[position['id']]
            if m['timestamp'] > cutoff_time
        ]
    
    async def _update_dashboard(self):
        """대시보드 데이터 업데이트"""
        
        dashboard_data = {
            'timestamp': datetime.now().isoformat(),
            'positions': len(self.monitors),
            'total_pnl': sum(m['pnl'] for metrics in self.metrics_history.values() 
                           for m in metrics[-1:]),  # 최신 PnL만
            'alerts': self.alerts[-10:],  # 최근 10개 알림
            'metrics': dict(self.metrics_history)
        }
        
        # WebSocket으로 전송 또는 파일 저장
        with open('/tmp/dashboard_data.json', 'w') as f:
            json.dump(dashboard_data, f, default=str)

# ===========================
# 통합 사용 예시
# ===========================

async def integrated_position_management_example():
    """통합 포지션 관리 시스템 사용 예시"""
    
    # 설정
    position_config = PositionConfig(
        base_size=Decimal(5000),
        max_slippage_percent=1.0,
        min_gap_percent=1.5,
        optimal_gap_percent=3.0,
        enable_split_orders=True
    )
    
    # 매니저 초기화
    position_manager = DynamicPositionManager(position_config)
    risk_controller = AdvancedRiskController()
    monitor = RealTimeMonitor()
    
    # 차익거래 기회
    opportunity = {
        'price_gap_percent': 2.5,
        'platform': 'polymarket',
        'market_id': 'abc123',
        'side': 'buy',
        'entry_price': Decimal('0.60')
    }
    
    # 시장 상황
    market_conditions = MarketConditions(
        volatility=0.3,
        liquidity_score=0.7,
        spread_percentage=0.5,
        recent_volume=Decimal(100000),
        price_trend='stable',
        confidence_level=0.8
    )
    
    # 오더북 (예시)
    orderbook = {
        'asks': [
            {'price': 0.60, 'size': 1000},
            {'price': 0.61, 'size': 2000},
            {'price': 0.62, 'size': 3000}
        ],
        'bids': [
            {'price': 0.59, 'size': 1500},
            {'price': 0.58, 'size': 2500}
        ]
    }
    
    # 1. 동적 포지션 크기 계산
    position_recommendation = position_manager.calculate_dynamic_position_size(
        opportunity,
        market_conditions,
        current_exposure=Decimal(20000),
        orderbook_depth=orderbook
    )
    
    print(f"Recommended position size: {position_recommendation['recommended_size']}")
    print(f"Split strategy: {position_recommendation['split_strategy']}")
    print(f"Confidence: {position_recommendation['confidence']:.2%}")
    print(f"Estimated slippage: {position_recommendation['estimated_slippage']:.2%}")
    
    # 2. 리스크 체크
    new_position = {
        'platform': opportunity['platform'],
        'size': position_recommendation['recommended_size'],
        'side': opportunity['side'],
        'category': 'crypto'
    }
    
    allowed, reason, risk_metrics = risk_controller.evaluate_position_entry(
        new_position,
        existing_positions=[],  # 기존 포지션들
        market_data={'volatility': 0.3, 'liquidity_score': 0.7}
    )
    
    print(f"\nRisk check: {'PASSED' if allowed else 'FAILED'}")
    print(f"Reason: {reason}")
    print(f"Risk level: {risk_metrics['risk_level']}")
    print(f"Recommendations: {risk_metrics['recommendations']}")
    
    # 3. 포지션 진입 결정
    if allowed and position_recommendation['confidence'] > 0.7:
        print("\n✅ Executing position entry with split orders...")
        
        for i, order in enumerate(position_recommendation['split_strategy']['orders']):
            print(f"Order {i+1}: Size={order['size']}, Delay={order['delay_ms']}ms")
            await asyncio.sleep(order['delay_ms'] / 1000)
            # 실제 주문 실행 로직
    else:
        print("\n❌ Position entry rejected")

if __name__ == "__main__":
    # 예시 실행
    asyncio.run(integrated_position_management_example())
