"""
Enhanced Market Matching Engine
강화된 마켓 매칭 엔진 (리졸브 소스/만기/타임존 검증)
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from dateutil import parser, tz
import re
import logging
from difflib import SequenceMatcher
import pytz

logger = logging.getLogger(__name__)

# ===========================
# 리졸브 소스 정의
# ===========================

RESOLUTION_SOURCES = {
    'UMA': {
        'reliability': 0.95,
        'delay_hours': 2,
        'platforms': ['polymarket'],
        'description': 'UMA Protocol (optimistic oracle)'
    },
    'Kalshi': {
        'reliability': 0.98,
        'delay_hours': 1,
        'platforms': ['kalshi'],
        'description': 'Kalshi official source (CFTC regulated)'
    },
    'Manifold': {
        'reliability': 0.75,
        'delay_hours': 0,
        'platforms': ['manifold'],
        'description': 'Community resolution'
    },
    'Reuters': {
        'reliability': 0.99,
        'delay_hours': 0.5,
        'platforms': ['polymarket', 'kalshi'],
        'description': 'Reuters news agency'
    },
    'AP': {
        'reliability': 0.99,
        'delay_hours': 0.5,
        'platforms': ['polymarket', 'kalshi'],
        'description': 'Associated Press'
    },
    'NYT': {
        'reliability': 0.97,
        'delay_hours': 1,
        'platforms': ['polymarket'],
        'description': 'New York Times'
    },
    'CoinMarketCap': {
        'reliability': 0.95,
        'delay_hours': 0.1,
        'platforms': ['polymarket', 'manifold'],
        'description': 'CoinMarketCap API'
    },
    'CoinGecko': {
        'reliability': 0.95,
        'delay_hours': 0.1,
        'platforms': ['polymarket', 'manifold'],
        'description': 'CoinGecko API'
    }
}

# ===========================
# 데이터 모델
# ===========================

@dataclass
class MatchScore:
    """매칭 점수"""
    overall_score: float  # 0-1 전체 점수
    question_similarity: float  # 질문 유사도
    resolution_compatibility: float  # 리졸브 소스 호환성
    expiry_alignment: float  # 만기 일치도
    timezone_match: float  # 타임존 일치도
    is_acceptable: bool  # 70% 기준 통과 여부
    warnings: List[str]
    details: Dict

@dataclass
class MarketMatch:
    """마켓 매칭 결과"""
    market_a: Dict
    market_b: Dict
    match_score: MatchScore
    confidence: float
    recommended: bool
    risk_factors: List[str]

# ===========================
# 질문 유사도 분석기
# ===========================

class QuestionSimilarityAnalyzer:
    """질문 유사도 분석"""

    def __init__(self):
        # 공통 불용어 (의미 없는 단어)
        self.stopwords = {
            'will', 'be', 'the', 'a', 'an', 'is', 'are', 'was', 'were',
            'have', 'has', 'had', 'do', 'does', 'did', 'on', 'at', 'by',
            'in', 'to', 'of', 'for', 'and', 'or', 'but'
        }

    def calculate_similarity(
        self,
        question_a: str,
        question_b: str
    ) -> Tuple[float, Dict]:
        """
        질문 유사도 계산

        Returns:
            (similarity_score, details)
        """

        # 정규화
        q1_norm = self._normalize_question(question_a)
        q2_norm = self._normalize_question(question_b)

        # 1. 전체 문자열 유사도 (SequenceMatcher)
        seq_similarity = SequenceMatcher(None, q1_norm, q2_norm).ratio()

        # 2. 단어 기반 유사도 (Jaccard)
        words_a = set(self._tokenize(q1_norm))
        words_b = set(self._tokenize(q2_norm))

        # 불용어 제거
        words_a = words_a - self.stopwords
        words_b = words_b - self.stopwords

        if not words_a or not words_b:
            jaccard_similarity = 0.0
        else:
            intersection = words_a.intersection(words_b)
            union = words_a.union(words_b)
            jaccard_similarity = len(intersection) / len(union)

        # 3. 핵심 키워드 매칭
        keywords_a = self._extract_keywords(q1_norm)
        keywords_b = self._extract_keywords(q2_norm)

        keyword_match = len(keywords_a.intersection(keywords_b)) / max(
            len(keywords_a.union(keywords_b)), 1
        )

        # 4. 숫자/날짜 일치도
        numbers_a = self._extract_numbers(question_a)
        numbers_b = self._extract_numbers(question_b)

        number_match = 1.0 if numbers_a == numbers_b else 0.5 if numbers_a.intersection(numbers_b) else 0.0

        # 가중 평균
        weights = {
            'sequence': 0.25,
            'jaccard': 0.35,
            'keywords': 0.25,
            'numbers': 0.15
        }

        overall_similarity = (
            seq_similarity * weights['sequence'] +
            jaccard_similarity * weights['jaccard'] +
            keyword_match * weights['keywords'] +
            number_match * weights['numbers']
        )

        details = {
            'sequence_similarity': seq_similarity,
            'jaccard_similarity': jaccard_similarity,
            'keyword_match': keyword_match,
            'number_match': number_match,
            'common_keywords': list(keywords_a.intersection(keywords_b)),
            'unique_to_a': list(keywords_a - keywords_b),
            'unique_to_b': list(keywords_b - keywords_a)
        }

        return overall_similarity, details

    def _normalize_question(self, question: str) -> str:
        """질문 정규화"""
        # 소문자 변환
        normalized = question.lower()

        # 특수문자 제거 (일부 유지)
        normalized = re.sub(r'[^\w\s\d\$\%]', '', normalized)

        # 연속 공백 제거
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        return normalized

    def _tokenize(self, text: str) -> List[str]:
        """토큰화"""
        return text.split()

    def _extract_keywords(self, text: str) -> set:
        """핵심 키워드 추출"""
        # 간단한 버전: 길이 4자 이상 단어
        words = self._tokenize(text)
        keywords = {w for w in words if len(w) >= 4 and w not in self.stopwords}
        return keywords

    def _extract_numbers(self, text: str) -> set:
        """숫자/날짜 추출"""
        # 숫자 패턴 (100k, $100,000, 2025 등)
        pattern = r'\$?[\d,]+\.?\d*[kmb]?'
        numbers = re.findall(pattern, text.lower())
        return set(numbers)

# ===========================
# 리졸브 소스 검증기
# ===========================

class ResolutionSourceValidator:
    """리졸브 소스 검증"""

    def calculate_compatibility(
        self,
        source_a: str,
        source_b: str,
        market_a_platform: str,
        market_b_platform: str
    ) -> Tuple[float, List[str]]:
        """
        리졸브 소스 호환성 계산

        Returns:
            (compatibility_score, warnings)
        """

        warnings = []

        # 소스 정보 조회
        info_a = RESOLUTION_SOURCES.get(source_a)
        info_b = RESOLUTION_SOURCES.get(source_b)

        if not info_a:
            warnings.append(f"Unknown resolution source: {source_a}")
            info_a = {'reliability': 0.5, 'delay_hours': 24}

        if not info_b:
            warnings.append(f"Unknown resolution source: {source_b}")
            info_b = {'reliability': 0.5, 'delay_hours': 24}

        # 1. 동일 소스 = 완벽 호환
        if source_a == source_b:
            return 1.0, warnings

        # 2. 신뢰도 차이
        reliability_diff = abs(
            info_a.get('reliability', 0.5) - info_b.get('reliability', 0.5)
        )
        reliability_score = 1.0 - reliability_diff

        # 3. 해결 시간 차이
        delay_a = info_a.get('delay_hours', 24)
        delay_b = info_b.get('delay_hours', 24)
        delay_diff = abs(delay_a - delay_b)

        # 6시간 이상 차이면 리스크
        if delay_diff > 6:
            warnings.append(f"Large resolution delay difference: {delay_diff:.1f} hours")
            delay_score = 0.5
        else:
            delay_score = 1.0 - (delay_diff / 12)  # 12시간 차이 = 0점

        # 4. 플랫폼 호환성
        platforms_a = info_a.get('platforms', [])
        platforms_b = info_b.get('platforms', [])

        # 교차 사용 가능 여부
        if source_a in RESOLUTION_SOURCES and source_b in RESOLUTION_SOURCES:
            if market_a_platform in platforms_b or market_b_platform in platforms_a:
                platform_score = 0.9
            else:
                platform_score = 0.7
                warnings.append(
                    f"Resolution sources typically used on different platforms"
                )
        else:
            platform_score = 0.5

        # 종합 점수
        compatibility = (
            reliability_score * 0.4 +
            delay_score * 0.3 +
            platform_score * 0.3
        )

        return compatibility, warnings

# ===========================
# 만기 검증기
# ===========================

class ExpiryValidator:
    """만기 일치도 검증"""

    def calculate_alignment(
        self,
        expiry_a: datetime,
        expiry_b: datetime,
        timezone_a: Optional[str] = None,
        timezone_b: Optional[str] = None
    ) -> Tuple[float, List[str]]:
        """
        만기 일치도 계산

        Returns:
            (alignment_score, warnings)
        """

        warnings = []

        # 타임존 정규화
        exp_a = self._normalize_timezone(expiry_a, timezone_a)
        exp_b = self._normalize_timezone(expiry_b, timezone_b)

        # 시간 차이 계산
        time_diff = abs((exp_a - exp_b).total_seconds())
        hours_diff = time_diff / 3600
        days_diff = time_diff / 86400

        # 점수 계산
        if hours_diff == 0:
            alignment = 1.0
        elif hours_diff < 1:  # 1시간 이내
            alignment = 0.95
        elif hours_diff < 24:  # 1일 이내
            alignment = 0.85
            warnings.append(f"Expiry difference: {hours_diff:.1f} hours")
        elif days_diff < 7:  # 1주 이내
            alignment = 0.60
            warnings.append(f"Expiry difference: {days_diff:.1f} days")
        else:  # 1주 이상
            alignment = 0.30
            warnings.append(f"Large expiry difference: {days_diff:.1f} days - HIGH RISK")

        # 정확한 날짜 일치 확인
        if exp_a.date() == exp_b.date():
            # 같은 날짜면 보너스
            alignment = min(alignment + 0.1, 1.0)
        else:
            warnings.append(
                f"Different expiry dates: {exp_a.date()} vs {exp_b.date()}"
            )

        return alignment, warnings

    def _normalize_timezone(
        self,
        dt: datetime,
        tz_name: Optional[str] = None
    ) -> datetime:
        """타임존 정규화 (UTC 기준)"""

        if dt.tzinfo is None:
            # Naive datetime
            if tz_name:
                try:
                    tz_obj = pytz.timezone(tz_name)
                    dt = tz_obj.localize(dt)
                except:
                    # 기본 UTC
                    dt = pytz.utc.localize(dt)
            else:
                dt = pytz.utc.localize(dt)

        # UTC로 변환
        return dt.astimezone(pytz.utc)

# ===========================
# 타임존 검증기
# ===========================

class TimezoneValidator:
    """타임존 일치도 검증"""

    def calculate_match(
        self,
        timezone_a: Optional[str],
        timezone_b: Optional[str],
        expiry_a: datetime,
        expiry_b: datetime
    ) -> Tuple[float, List[str]]:
        """
        타임존 일치도 계산

        Returns:
            (match_score, warnings)
        """

        warnings = []

        # 타임존 정보가 없으면 경고
        if not timezone_a or not timezone_b:
            warnings.append("Missing timezone information")
            return 0.7, warnings

        # 동일 타임존
        if timezone_a == timezone_b:
            return 1.0, warnings

        # 타임존 오프셋 계산
        try:
            tz_a = pytz.timezone(timezone_a)
            tz_b = pytz.timezone(timezone_b)

            # 만기 시점의 오프셋 (DST 고려)
            offset_a = tz_a.utcoffset(expiry_a).total_seconds() / 3600
            offset_b = tz_b.utcoffset(expiry_b).total_seconds() / 3600

            offset_diff = abs(offset_a - offset_b)

            # 점수 계산
            if offset_diff == 0:
                match_score = 1.0
            elif offset_diff <= 1:
                match_score = 0.9
            elif offset_diff <= 3:
                match_score = 0.8
                warnings.append(f"Timezone offset difference: {offset_diff} hours")
            else:
                match_score = 0.6
                warnings.append(f"Large timezone offset difference: {offset_diff} hours")

        except Exception as e:
            logger.error(f"Timezone validation error: {e}")
            warnings.append(f"Timezone processing error: {e}")
            match_score = 0.5

        return match_score, warnings

# ===========================
# 통합 매칭 엔진
# ===========================

class EnhancedMatchingEngine:
    """강화된 마켓 매칭 엔진"""

    def __init__(
        self,
        min_overall_score: float = 0.70,  # 70% 기준
        min_question_similarity: float = 0.60,
        min_resolution_compatibility: float = 0.60,
        min_expiry_alignment: float = 0.60
    ):
        self.min_overall_score = min_overall_score
        self.min_question_similarity = min_question_similarity
        self.min_resolution_compatibility = min_resolution_compatibility
        self.min_expiry_alignment = min_expiry_alignment

        # 분석기들
        self.question_analyzer = QuestionSimilarityAnalyzer()
        self.resolution_validator = ResolutionSourceValidator()
        self.expiry_validator = ExpiryValidator()
        self.timezone_validator = TimezoneValidator()

    def match_markets(
        self,
        market_a: Dict,
        market_b: Dict
    ) -> MarketMatch:
        """
        두 마켓 매칭 검증

        Args:
            market_a: {
                'platform': 'polymarket',
                'question': 'Will...',
                'resolution_source': 'UMA',
                'expiry_date': datetime(...),
                'timezone': 'America/New_York',
                ...
            }
            market_b: Similar structure

        Returns:
            MarketMatch object
        """

        warnings = []
        risk_factors = []

        # 1. 질문 유사도
        question_sim, q_details = self.question_analyzer.calculate_similarity(
            market_a.get('question', ''),
            market_b.get('question', '')
        )

        if question_sim < self.min_question_similarity:
            risk_factors.append(
                f"Low question similarity: {question_sim:.2%}"
            )

        # 2. 리졸브 소스 호환성
        resolution_compat, res_warnings = self.resolution_validator.calculate_compatibility(
            market_a.get('resolution_source', 'Unknown'),
            market_b.get('resolution_source', 'Unknown'),
            market_a.get('platform', ''),
            market_b.get('platform', '')
        )
        warnings.extend(res_warnings)

        if resolution_compat < self.min_resolution_compatibility:
            risk_factors.append(
                f"Low resolution compatibility: {resolution_compat:.2%}"
            )

        # 3. 만기 일치도
        expiry_alignment, exp_warnings = self.expiry_validator.calculate_alignment(
            market_a.get('expiry_date'),
            market_b.get('expiry_date'),
            market_a.get('timezone'),
            market_b.get('timezone')
        )
        warnings.extend(exp_warnings)

        if expiry_alignment < self.min_expiry_alignment:
            risk_factors.append(
                f"Low expiry alignment: {expiry_alignment:.2%}"
            )

        # 4. 타임존 일치도
        timezone_match, tz_warnings = self.timezone_validator.calculate_match(
            market_a.get('timezone'),
            market_b.get('timezone'),
            market_a.get('expiry_date'),
            market_b.get('expiry_date')
        )
        warnings.extend(tz_warnings)

        # 전체 점수 계산 (가중 평균)
        weights = {
            'question': 0.35,
            'resolution': 0.30,
            'expiry': 0.25,
            'timezone': 0.10
        }

        overall_score = (
            question_sim * weights['question'] +
            resolution_compat * weights['resolution'] +
            expiry_alignment * weights['expiry'] +
            timezone_match * weights['timezone']
        )

        # 70% 기준 통과 여부
        is_acceptable = overall_score >= self.min_overall_score

        # 매칭 점수 객체
        match_score = MatchScore(
            overall_score=overall_score,
            question_similarity=question_sim,
            resolution_compatibility=resolution_compat,
            expiry_alignment=expiry_alignment,
            timezone_match=timezone_match,
            is_acceptable=is_acceptable,
            warnings=warnings,
            details=q_details
        )

        # 신뢰도 계산
        confidence = self._calculate_confidence(
            match_score, len(risk_factors)
        )

        # 추천 여부
        recommended = (
            is_acceptable and
            confidence > 0.7 and
            len(risk_factors) <= 2
        )

        return MarketMatch(
            market_a=market_a,
            market_b=market_b,
            match_score=match_score,
            confidence=confidence,
            recommended=recommended,
            risk_factors=risk_factors
        )

    def _calculate_confidence(
        self,
        match_score: MatchScore,
        risk_count: int
    ) -> float:
        """신뢰도 계산"""

        # 기본 신뢰도 = 전체 점수
        confidence = match_score.overall_score

        # 리스크 요인 페널티
        confidence *= (1.0 - risk_count * 0.1)

        # 경고 페널티
        confidence *= (1.0 - len(match_score.warnings) * 0.05)

        return max(0.0, min(confidence, 1.0))

    def find_matches(
        self,
        markets: List[Dict],
        only_recommended: bool = True
    ) -> List[MarketMatch]:
        """
        마켓 리스트에서 모든 매칭 찾기

        Args:
            markets: 마켓 리스트
            only_recommended: 추천 매칭만 반환

        Returns:
            매칭 리스트 (점수 순 정렬)
        """

        matches = []

        for i in range(len(markets)):
            for j in range(i + 1, len(markets)):
                market_a = markets[i]
                market_b = markets[j]

                # 같은 플랫폼끼리는 매칭 불필요
                if market_a.get('platform') == market_b.get('platform'):
                    continue

                match = self.match_markets(market_a, market_b)

                if only_recommended:
                    if match.recommended:
                        matches.append(match)
                else:
                    if match.match_score.is_acceptable:
                        matches.append(match)

        # 점수 순 정렬
        matches.sort(key=lambda x: x.match_score.overall_score, reverse=True)

        return matches

    def print_match(self, match: MarketMatch):
        """매칭 결과 출력"""
        score = match.match_score

        print("\n" + "="*70)
        print(f"{'🟢 RECOMMENDED' if match.recommended else '🟡 ACCEPTABLE'} MATCH "
              f"(Overall: {score.overall_score:.1%})")
        print("="*70)

        print(f"\n📊 Market A: {match.market_a.get('platform', 'Unknown').upper()}")
        print(f"   Question: {match.market_a.get('question', 'N/A')[:60]}...")
        print(f"   Resolution: {match.market_a.get('resolution_source', 'N/A')}")
        print(f"   Expiry: {match.market_a.get('expiry_date', 'N/A')}")

        print(f"\n📊 Market B: {match.market_b.get('platform', 'Unknown').upper()}")
        print(f"   Question: {match.market_b.get('question', 'N/A')[:60]}...")
        print(f"   Resolution: {match.market_b.get('resolution_source', 'N/A')}")
        print(f"   Expiry: {match.market_b.get('expiry_date', 'N/A')}")

        print(f"\n📈 Matching Scores:")
        print(f"   Question Similarity:       {score.question_similarity:.1%}")
        print(f"   Resolution Compatibility:  {score.resolution_compatibility:.1%}")
        print(f"   Expiry Alignment:          {score.expiry_alignment:.1%}")
        print(f"   Timezone Match:            {score.timezone_match:.1%}")
        print(f"   Overall Score:             {score.overall_score:.1%}")

        print(f"\n✅ Validation:")
        print(f"   Meets 70% Threshold: {'YES ✓' if score.is_acceptable else 'NO ✗'}")
        print(f"   Confidence:          {match.confidence:.1%}")
        print(f"   Recommended:         {'YES ✓' if match.recommended else 'NO ✗'}")

        if match.risk_factors:
            print(f"\n⚠️  Risk Factors:")
            for risk in match.risk_factors:
                print(f"   - {risk}")

        if score.warnings:
            print(f"\n⚡ Warnings:")
            for warning in score.warnings:
                print(f"   - {warning}")

        print("="*70 + "\n")

# ===========================
# 사용 예시
# ===========================

async def example_usage():
    """매칭 엔진 사용 예시"""

    # 샘플 마켓
    market_poly = {
        'platform': 'polymarket',
        'market_id': 'abc123',
        'question': 'Will Bitcoin reach $100,000 by December 31, 2025?',
        'resolution_source': 'CoinMarketCap',
        'expiry_date': datetime(2025, 12, 31, 23, 59, 59),
        'timezone': 'America/New_York',
        'liquidity': 500000
    }

    market_kalshi = {
        'platform': 'kalshi',
        'market_id': 'xyz789',
        'question': 'BTC above $100k by end of 2025?',
        'resolution_source': 'CoinGecko',
        'expiry_date': datetime(2025, 12, 31, 20, 0, 0),  # 3시간 차이 (PST)
        'timezone': 'America/Los_Angeles',
        'liquidity': 300000
    }

    # 매칭 엔진 생성
    engine = EnhancedMatchingEngine(min_overall_score=0.70)

    # 매칭 검증
    print("🔍 Matching markets...\n")
    match = engine.match_markets(market_poly, market_kalshi)

    # 결과 출력
    engine.print_match(match)

    # 배치 매칭
    print("\n\n🔎 Batch Matching Example:")
    markets = [market_poly, market_kalshi]
    matches = engine.find_matches(markets, only_recommended=True)

    print(f"Found {len(matches)} recommended matches")

if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())
