"""
Advanced Slippage Management & Smart Order Execution System
슬리피지 관리 및 스마트 주문 분할 시스템
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from decimal import Decimal, getcontext
import asyncio
from collections import deque
import math

# 정밀한 계산을 위한 Decimal 설정
getcontext().prec = 10

@dataclass
class OrderBookLevel:
    """오더북 레벨 데이터"""
    price: Decimal
    size: Decimal
    cumulative_size: Decimal = Decimal(0)
    
@dataclass
class SlippageEstimate:
    """슬리피지 예측 결과"""
    avg_price: Decimal
    total_slippage: Decimal
    slippage_percentage: float
    effective_profit: float
    recommended_size: Decimal
    split_orders: List[Dict]

@dataclass
class OrderSplit:
    """분할 주문 정보"""
    size: Decimal
    price: Decimal
    delay_ms: int  # 주문 간 지연 시간
    platform: str
    side: str

# ===========================
# 슬리피지 계산 엔진
# ===========================

class SlippageCalculator:
    """슬리피지 계산 및 예측 엔진"""
    
    def __init__(self, max_slippage_percent: float = 1.0):
        self.max_slippage_percent = max_slippage_percent
        self.historical_slippage = deque(maxlen=100)  # 최근 100개 거래 기록
        
    def calculate_market_impact(
        self,
        order_size: Decimal,
        orderbook: Dict[str, List[OrderBookLevel]],
        side: str = 'buy'
    ) -> SlippageEstimate:
        """
        주문 크기에 따른 시장 영향도 계산
        
        Args:
            order_size: 주문 크기
            orderbook: 오더북 데이터
            side: 'buy' or 'sell'
        """
        levels = orderbook.get('asks' if side == 'buy' else 'bids', [])
        
        if not levels:
            return SlippageEstimate(
                avg_price=Decimal(0),
                total_slippage=Decimal(0),
                slippage_percentage=0,
                effective_profit=0,
                recommended_size=Decimal(0),
                split_orders=[]
            )
        
        # 누적 크기 계산
        cumulative_size = Decimal(0)
        cumulative_cost = Decimal(0)
        filled_levels = []
        
        for level in levels:
            if cumulative_size >= order_size:
                break
                
            fill_size = min(level.size, order_size - cumulative_size)
            cumulative_size += fill_size
            cumulative_cost += fill_size * level.price
            
            filled_levels.append({
                'price': level.price,
                'size': fill_size,
                'level_index': len(filled_levels)
            })
        
        if cumulative_size == 0:
            return SlippageEstimate(
                avg_price=Decimal(0),
                total_slippage=Decimal(0),
                slippage_percentage=0,
                effective_profit=0,
                recommended_size=Decimal(0),
                split_orders=[]
            )
        
        # 평균 체결 가격
        avg_price = cumulative_cost / cumulative_size
        
        # 최고호가 대비 슬리피지
        best_price = levels[0].price
        total_slippage = avg_price - best_price if side == 'buy' else best_price - avg_price
        slippage_percentage = float((total_slippage / best_price) * 100)
        
        # 슬리피지 고려한 실효 수익률
        effective_profit = self._calculate_effective_profit(
            avg_price, slippage_percentage
        )
        
        # 권장 주문 크기 (슬리피지 제한 내)
        recommended_size = self._calculate_recommended_size(
            levels, self.max_slippage_percent
        )
        
        # 주문 분할 계획
        split_orders = self._generate_split_orders(
            order_size, levels, slippage_percentage
        )
        
        return SlippageEstimate(
            avg_price=avg_price,
            total_slippage=total_slippage,
            slippage_percentage=slippage_percentage,
            effective_profit=effective_profit,
            recommended_size=recommended_size,
            split_orders=split_orders
        )
    
    def _calculate_effective_profit(
        self,
        avg_price: Decimal,
        slippage_percentage: float
    ) -> float:
        """슬리피지 반영한 실제 수익률 계산"""
        # 기본 수익률에서 슬리피지 차감
        base_profit = 2.0  # 예시: 기본 차익거래 수익률 2%
        effective_profit = base_profit - slippage_percentage
        return max(0, effective_profit)
    
    def _calculate_recommended_size(
        self,
        levels: List[OrderBookLevel],
        max_slippage: float
    ) -> Decimal:
        """최대 슬리피지 내에서 가능한 주문 크기 계산"""
        if not levels:
            return Decimal(0)
            
        best_price = levels[0].price
        max_price_deviation = best_price * Decimal(max_slippage / 100)
        
        recommended_size = Decimal(0)
        for level in levels:
            if abs(level.price - best_price) > max_price_deviation:
                break
            recommended_size += level.size
        
        return recommended_size
    
    def _generate_split_orders(
        self,
        total_size: Decimal,
        levels: List[OrderBookLevel],
        current_slippage: float
    ) -> List[Dict]:
        """주문 분할 계획 생성"""
        if current_slippage < self.max_slippage_percent:
            # 슬리피지가 허용 범위 내면 단일 주문
            return [{
                'size': total_size,
                'type': 'market',
                'delay_ms': 0
            }]
        
        # 슬리피지가 크면 분할 주문
        split_count = math.ceil(current_slippage / self.max_slippage_percent)
        split_size = total_size / split_count
        
        orders = []
        for i in range(split_count):
            orders.append({
                'size': split_size,
                'type': 'limit' if i > 0 else 'market',  # 첫 주문은 시장가
                'delay_ms': i * 1000,  # 1초씩 지연
                'price_offset': i * 0.001  # 가격 오프셋
            })
        
        return orders

# ===========================
# 스마트 주문 실행 엔진
# ===========================

class SmartOrderExecutor:
    """스마트 주문 실행 및 분할 시스템"""
    
    def __init__(
        self,
        slippage_calculator: SlippageCalculator,
        max_order_size: Decimal = Decimal(10000),
        min_order_size: Decimal = Decimal(100)
    ):
        self.slippage_calc = slippage_calculator
        self.max_order_size = max_order_size
        self.min_order_size = min_order_size
        self.pending_orders = []
        self.executed_orders = []
        
    async def execute_with_slippage_control(
        self,
        platform_client,
        market_id: str,
        side: str,
        size: Decimal,
        orderbook: Dict,
        max_slippage: float = 1.0
    ) -> Dict:
        """
        슬리피지 제어를 통한 스마트 주문 실행
        
        Args:
            platform_client: 플랫폼 API 클라이언트
            market_id: 마켓 ID
            side: 'buy' or 'sell'
            size: 총 주문 크기
            orderbook: 오더북 데이터
            max_slippage: 최대 허용 슬리피지 (%)
        """
        
        # 슬리피지 예측
        slippage_estimate = self.slippage_calc.calculate_market_impact(
            size, orderbook, side
        )
        
        # 슬리피지가 허용 범위를 초과하는 경우
        if slippage_estimate.slippage_percentage > max_slippage:
            return await self._execute_split_orders(
                platform_client,
                market_id,
                side,
                size,
                orderbook,
                slippage_estimate
            )
        
        # 단일 주문으로 실행 가능한 경우
        return await self._execute_single_order(
            platform_client,
            market_id,
            side,
            size,
            slippage_estimate.avg_price
        )
    
    async def _execute_split_orders(
        self,
        platform_client,
        market_id: str,
        side: str,
        total_size: Decimal,
        orderbook: Dict,
        slippage_estimate: SlippageEstimate
    ) -> Dict:
        """분할 주문 실행"""
        
        results = {
            'status': 'executing',
            'total_size': total_size,
            'filled_size': Decimal(0),
            'avg_price': Decimal(0),
            'orders': [],
            'slippage': slippage_estimate.slippage_percentage
        }
        
        # 주문 분할 계획
        split_orders = self._optimize_order_splits(
            total_size,
            orderbook,
            slippage_estimate
        )
        
        total_filled = Decimal(0)
        total_cost = Decimal(0)
        
        for split_order in split_orders:
            # 지연 시간 적용
            if split_order['delay_ms'] > 0:
                await asyncio.sleep(split_order['delay_ms'] / 1000)
            
            # 오더북 재조회 (시장 상황 변화 반영)
            updated_orderbook = await platform_client.get_market_orderbook(market_id)
            
            # 적응형 주문 크기 조정
            adjusted_size = self._adjust_order_size(
                split_order['size'],
                updated_orderbook,
                results['filled_size'],
                total_size
            )
            
            if adjusted_size < self.min_order_size:
                continue
            
            # 주문 실행
            if split_order['type'] == 'market':
                order_result = await platform_client.place_market_order(
                    market_id, side, adjusted_size
                )
            else:
                # Limit 주문 (더 나은 가격 시도)
                limit_price = self._calculate_limit_price(
                    updated_orderbook, side, split_order.get('price_offset', 0)
                )
                order_result = await platform_client.place_limit_order(
                    market_id, side, adjusted_size, limit_price
                )
            
            if order_result.get('status') == 'filled':
                filled_size = Decimal(str(order_result['filled_size']))
                fill_price = Decimal(str(order_result['avg_price']))
                
                total_filled += filled_size
                total_cost += filled_size * fill_price
                
                results['orders'].append({
                    'order_id': order_result['order_id'],
                    'size': filled_size,
                    'price': fill_price,
                    'timestamp': order_result['timestamp']
                })
            
            # 목표 크기 도달 시 종료
            if total_filled >= total_size * Decimal('0.95'):  # 95% 체결 시
                break
        
        # 최종 결과 계산
        if total_filled > 0:
            results['filled_size'] = total_filled
            results['avg_price'] = total_cost / total_filled
            results['status'] = 'completed'
            
            # 실제 슬리피지 계산
            best_price = Decimal(str(orderbook['asks'][0]['price'] if side == 'buy' else orderbook['bids'][0]['price']))
            actual_slippage = float((results['avg_price'] - best_price) / best_price * 100)
            results['actual_slippage'] = actual_slippage
        else:
            results['status'] = 'failed'
        
        return results
    
    async def _execute_single_order(
        self,
        platform_client,
        market_id: str,
        side: str,
        size: Decimal,
        expected_price: Decimal
    ) -> Dict:
        """단일 주문 실행"""
        
        order_result = await platform_client.place_market_order(
            market_id, side, size
        )
        
        return {
            'status': order_result.get('status', 'failed'),
            'total_size': size,
            'filled_size': Decimal(str(order_result.get('filled_size', 0))),
            'avg_price': Decimal(str(order_result.get('avg_price', 0))),
            'orders': [order_result],
            'slippage': 0
        }
    
    def _optimize_order_splits(
        self,
        total_size: Decimal,
        orderbook: Dict,
        slippage_estimate: SlippageEstimate
    ) -> List[Dict]:
        """최적 주문 분할 전략 생성"""
        
        # 오더북 깊이 분석
        liquidity_levels = self._analyze_liquidity_depth(orderbook)
        
        # 분할 전략 결정
        if len(liquidity_levels) == 0:
            # 유동성 부족 - 최소 단위로 분할
            return self._create_minimal_splits(total_size)
        
        # 유동성 레벨별 주문 분할
        splits = []
        remaining_size = total_size
        
        for level in liquidity_levels:
            if remaining_size <= 0:
                break
                
            # 각 유동성 레벨에서 최적 크기 계산
            optimal_size = min(
                remaining_size,
                level['available_size'] * Decimal('0.3')  # 레벨별 30% 이하
            )
            
            if optimal_size >= self.min_order_size:
                splits.append({
                    'size': optimal_size,
                    'type': 'limit' if len(splits) > 0 else 'market',
                    'delay_ms': len(splits) * 500,  # 0.5초씩 증가
                    'price_offset': level['price_offset']
                })
                remaining_size -= optimal_size
        
        # 남은 수량 처리
        if remaining_size > self.min_order_size:
            splits.append({
                'size': remaining_size,
                'type': 'limit',
                'delay_ms': len(splits) * 500,
                'price_offset': 0.002
            })
        
        return splits
    
    def _analyze_liquidity_depth(self, orderbook: Dict) -> List[Dict]:
        """오더북 유동성 깊이 분석"""
        levels = []
        
        for side in ['bids', 'asks']:
            if side not in orderbook:
                continue
                
            current_levels = orderbook[side]
            if not current_levels:
                continue
            
            best_price = Decimal(str(current_levels[0]['price']))
            
            # 가격 레벨별 유동성 분석
            for i, level in enumerate(current_levels[:10]):  # 상위 10개 레벨
                price = Decimal(str(level['price']))
                size = Decimal(str(level['size']))
                
                price_offset = abs(price - best_price) / best_price
                
                levels.append({
                    'price': price,
                    'available_size': size,
                    'price_offset': float(price_offset),
                    'depth': i
                })
        
        # 가격 오프셋 기준 정렬
        levels.sort(key=lambda x: x['price_offset'])
        
        return levels
    
    def _adjust_order_size(
        self,
        planned_size: Decimal,
        current_orderbook: Dict,
        already_filled: Decimal,
        total_target: Decimal
    ) -> Decimal:
        """시장 상황에 따른 주문 크기 동적 조정"""
        
        # 남은 목표 수량
        remaining_target = total_target - already_filled
        
        # 현재 이용 가능한 유동성
        available_liquidity = self._get_available_liquidity(current_orderbook)
        
        # 조정된 크기 계산
        adjusted = min(
            planned_size,
            remaining_target,
            available_liquidity * Decimal('0.5')  # 가용 유동성의 50%
        )
        
        # 최소/최대 크기 제한
        adjusted = max(self.min_order_size, min(adjusted, self.max_order_size))
        
        return adjusted
    
    def _get_available_liquidity(self, orderbook: Dict) -> Decimal:
        """현재 가용 유동성 계산"""
        total_liquidity = Decimal(0)
        
        for side in ['bids', 'asks']:
            if side in orderbook:
                for level in orderbook[side][:5]:  # 상위 5개 레벨
                    total_liquidity += Decimal(str(level.get('size', 0)))
        
        return total_liquidity
    
    def _calculate_limit_price(
        self,
        orderbook: Dict,
        side: str,
        price_offset: float
    ) -> Decimal:
        """리밋 주문 가격 계산"""
        
        if side == 'buy':
            best_ask = Decimal(str(orderbook['asks'][0]['price']))
            # 매수: 최고 매도호가보다 약간 낮게
            return best_ask * (Decimal(1) - Decimal(str(price_offset)))
        else:
            best_bid = Decimal(str(orderbook['bids'][0]['price']))
            # 매도: 최고 매수호가보다 약간 높게
            return best_bid * (Decimal(1) + Decimal(str(price_offset)))

# ===========================
# 적응형 포지션 사이징
# ===========================

class AdaptivePositionSizer:
    """시장 상황에 따른 적응형 포지션 크기 결정"""
    
    def __init__(
        self,
        base_position_size: Decimal = Decimal(10000),
        min_profit_after_slippage: float = 0.5
    ):
        self.base_position_size = base_position_size
        self.min_profit_after_slippage = min_profit_after_slippage
        self.historical_fills = deque(maxlen=50)
        
    def calculate_optimal_position(
        self,
        opportunity_profit: float,
        market1_orderbook: Dict,
        market2_orderbook: Dict,
        slippage_calculator: SlippageCalculator
    ) -> Dict:
        """
        최적 포지션 크기 계산
        
        Args:
            opportunity_profit: 기회 수익률 (%)
            market1_orderbook: 마켓1 오더북
            market2_orderbook: 마켓2 오더북
            slippage_calculator: 슬리피지 계산기
        """
        
        # 다양한 포지션 크기에 대한 슬리피지 시뮬레이션
        test_sizes = [
            self.base_position_size * Decimal(str(mult))
            for mult in [0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0]
        ]
        
        optimal = {
            'size': Decimal(0),
            'expected_profit': 0,
            'market1_slippage': 0,
            'market2_slippage': 0,
            'net_profit': 0,
            'confidence': 0
        }
        
        for test_size in test_sizes:
            # 각 마켓에서 슬리피지 계산
            m1_slippage = slippage_calculator.calculate_market_impact(
                test_size, market1_orderbook, 'buy'
            )
            m2_slippage = slippage_calculator.calculate_market_impact(
                test_size, market2_orderbook, 'buy'
            )
            
            # 총 슬리피지
            total_slippage = m1_slippage.slippage_percentage + m2_slippage.slippage_percentage
            
            # 슬리피지 차감 후 순수익
            net_profit = opportunity_profit - total_slippage
            
            # 최소 수익률 충족 여부
            if net_profit >= self.min_profit_after_slippage:
                # 수익 * 크기로 절대 수익 계산
                absolute_profit = float(test_size) * (net_profit / 100)
                
                if absolute_profit > optimal['expected_profit']:
                    optimal = {
                        'size': test_size,
                        'expected_profit': absolute_profit,
                        'market1_slippage': m1_slippage.slippage_percentage,
                        'market2_slippage': m2_slippage.slippage_percentage,
                        'net_profit': net_profit,
                        'confidence': self._calculate_confidence(
                            net_profit, total_slippage, test_size
                        )
                    }
        
        return optimal
    
    def _calculate_confidence(
        self,
        net_profit: float,
        total_slippage: float,
        size: Decimal
    ) -> float:
        """포지션 신뢰도 계산"""
        
        # 수익률 기반 점수
        profit_score = min(net_profit / 5.0, 1.0)  # 5% 수익 = 만점
        
        # 슬리피지 기반 점수 (낮을수록 좋음)
        slippage_score = max(0, 1.0 - (total_slippage / 2.0))  # 2% 슬리피지 = 0점
        
        # 크기 기반 점수 (적정 크기일수록 좋음)
        size_ratio = float(size / self.base_position_size)
        size_score = 1.0 if 0.5 <= size_ratio <= 1.5 else 0.7
        
        # 종합 신뢰도
        confidence = (profit_score * 0.5 + slippage_score * 0.3 + size_score * 0.2)
        
        return min(max(confidence, 0), 1.0)

# ===========================
# 통합 실행 시스템
# ===========================

class EnhancedArbitrageExecutor:
    """슬리피지 관리가 통합된 차익거래 실행 시스템"""
    
    def __init__(
        self,
        polymarket_client,
        kalshi_client,
        manifold_client,
        config: Dict
    ):
        self.clients = {
            'polymarket': polymarket_client,
            'kalshi': kalshi_client,
            'manifold': manifold_client
        }
        
        # 슬리피지 관리 컴포넌트
        self.slippage_calc = SlippageCalculator(
            max_slippage_percent=config.get('max_slippage', 1.0)
        )
        
        self.order_executor = SmartOrderExecutor(
            slippage_calculator=self.slippage_calc,
            max_order_size=Decimal(str(config.get('max_order_size', 10000))),
            min_order_size=Decimal(str(config.get('min_order_size', 100)))
        )
        
        self.position_sizer = AdaptivePositionSizer(
            base_position_size=Decimal(str(config.get('base_position_size', 10000))),
            min_profit_after_slippage=config.get('min_profit_after_slippage', 0.5)
        )
        
        self.config = config
        
    async def execute_arbitrage_with_slippage_control(
        self,
        opportunity: Dict
    ) -> Dict:
        """
        슬리피지 제어를 통한 차익거래 실행
        
        Args:
            opportunity: 차익거래 기회 정보
        """
        
        result = {
            'status': 'pending',
            'opportunity': opportunity,
            'trades': [],
            'total_invested': Decimal(0),
            'expected_profit': Decimal(0),
            'actual_profit': None,
            'slippage_report': {}
        }
        
        try:
            # 1. 양쪽 마켓 오더북 조회
            m1_orderbook = await self._get_orderbook(
                opportunity['market1']['platform'],
                opportunity['market1']['market_id']
            )
            m2_orderbook = await self._get_orderbook(
                opportunity['market2']['platform'],
                opportunity['market2']['market_id']
            )
            
            # 2. 최적 포지션 크기 계산
            optimal_position = self.position_sizer.calculate_optimal_position(
                opportunity['profit_percentage'],
                m1_orderbook,
                m2_orderbook,
                self.slippage_calc
            )
            
            # 3. 순수익이 최소 기준 미달 시 중단
            if optimal_position['net_profit'] < self.config.get('min_profit_after_slippage', 0.5):
                result['status'] = 'skipped'
                result['reason'] = f"Net profit after slippage ({optimal_position['net_profit']:.2f}%) below minimum"
                return result
            
            # 4. 스마트 주문 실행 (양쪽 동시)
            trade_tasks = [
                self._execute_smart_trade(
                    opportunity['market1'],
                    optimal_position['size'],
                    m1_orderbook
                ),
                self._execute_smart_trade(
                    opportunity['market2'],
                    optimal_position['size'],
                    m2_orderbook
                )
            ]
            
            trade_results = await asyncio.gather(*trade_tasks)
            
            # 5. 결과 분석
            all_filled = all(t['status'] == 'completed' for t in trade_results)
            
            if all_filled:
                result['status'] = 'completed'
                result['trades'] = trade_results
                
                # 실제 투자금 및 슬리피지 계산
                for trade in trade_results:
                    result['total_invested'] += trade['filled_size'] * trade['avg_price']
                    
                result['slippage_report'] = {
                    'market1': {
                        'expected': optimal_position['market1_slippage'],
                        'actual': trade_results[0].get('actual_slippage', 0)
                    },
                    'market2': {
                        'expected': optimal_position['market2_slippage'],
                        'actual': trade_results[1].get('actual_slippage', 0)
                    },
                    'total_impact': sum(t.get('actual_slippage', 0) for t in trade_results)
                }
                
                # 실제 수익 계산
                total_actual_slippage = result['slippage_report']['total_impact']
                result['actual_profit'] = opportunity['profit_percentage'] - total_actual_slippage
                
            else:
                result['status'] = 'partial'
                result['trades'] = trade_results
                
                # 부분 체결 처리 로직
                await self._handle_partial_fill(result, trade_results)
                
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            
        return result
    
    async def _get_orderbook(self, platform: str, market_id: str) -> Dict:
        """플랫폼별 오더북 조회"""
        client = self.clients.get(platform)
        if not client:
            raise ValueError(f"Unknown platform: {platform}")
            
        return await client.get_market_orderbook(market_id)
    
    async def _execute_smart_trade(
        self,
        market: Dict,
        size: Decimal,
        orderbook: Dict
    ) -> Dict:
        """스마트 거래 실행"""
        
        platform = market['platform']
        client = self.clients.get(platform)
        
        return await self.order_executor.execute_with_slippage_control(
            platform_client=client,
            market_id=market['market_id'],
            side=market['side'],
            size=size,
            orderbook=orderbook,
            max_slippage=self.config.get('max_slippage', 1.0)
        )
    
    async def _handle_partial_fill(self, result: Dict, trade_results: List[Dict]):
        """부분 체결 처리"""
        
        # 체결된 부분만 계산
        filled_trades = [t for t in trade_results if t['filled_size'] > 0]
        
        if len(filled_trades) == 1:
            # 한쪽만 체결된 경우 - 반대 포지션으로 헤지
            unfilled_side = 0 if trade_results[1]['filled_size'] > 0 else 1
            
            # 헤지 주문 실행
            hedge_result = await self._execute_hedge_order(
                result['opportunity'][f'market{unfilled_side + 1}'],
                filled_trades[0]['filled_size']
            )
            
            result['hedge'] = hedge_result
            
        # 부분 체결 정보 업데이트
        result['partial_fill_info'] = {
            'filled_count': len(filled_trades),
            'total_filled': sum(t['filled_size'] for t in filled_trades),
            'recovery_action': 'hedge' if len(filled_trades) == 1 else 'none'
        }
    
    async def _execute_hedge_order(self, market: Dict, size: Decimal) -> Dict:
        """헤지 주문 실행"""
        
        # 반대 방향으로 주문
        opposite_side = 'sell' if market['side'] == 'buy' else 'buy'
        
        client = self.clients.get(market['platform'])
        return await client.place_market_order(
            market['market_id'],
            opposite_side,
            size
        )

# ===========================
# 사용 예시
# ===========================

async def example_usage():
    """슬리피지 관리 시스템 사용 예시"""
    
    # 설정
    config = {
        'max_slippage': 1.0,  # 최대 슬리피지 1%
        'max_order_size': 10000,
        'min_order_size': 100,
        'base_position_size': 5000,
        'min_profit_after_slippage': 0.5  # 슬리피지 후 최소 0.5% 수익
    }
    
    # 실행자 생성
    executor = EnhancedArbitrageExecutor(
        polymarket_client=None,  # 실제 클라이언트
        kalshi_client=None,
        manifold_client=None,
        config=config
    )
    
    # 차익거래 기회
    opportunity = {
        'market1': {
            'platform': 'polymarket',
            'market_id': 'xxx',
            'side': 'buy',
            'price': 0.60
        },
        'market2': {
            'platform': 'kalshi',
            'market_id': 'yyy',
            'side': 'sell',
            'price': 0.45
        },
        'profit_percentage': 5.0  # 기본 수익률 5%
    }
    
    # 실행
    result = await executor.execute_arbitrage_with_slippage_control(opportunity)
    
    print(f"Status: {result['status']}")
    print(f"Expected profit: {opportunity['profit_percentage']}%")
    print(f"Actual profit after slippage: {result.get('actual_profit', 'N/A')}%")
    print(f"Slippage impact: {result['slippage_report']}")

if __name__ == "__main__":
    # 예시 실행
    asyncio.run(example_usage())
