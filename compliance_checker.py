"""
Compliance & Access Control System
규제 준수 및 접근성 제어 시스템
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class ComplianceCheck:
    """규제 체크 결과"""
    platform: str
    allowed: bool
    reason: str
    risk_level: str  # 'low', 'medium', 'high', 'critical'
    restrictions: List[str]
    timestamp: datetime

@dataclass
class UserLocation:
    """사용자 위치 정보"""
    country: str
    country_code: str
    region: str
    city: str
    ip_address: str
    is_vpn: bool
    is_proxy: bool
    is_tor: bool

# ===========================
# 플랫폼별 규제 정책
# ===========================

PLATFORM_RESTRICTIONS = {
    'polymarket': {
        'blocked_countries': ['US', 'KP', 'IR', 'SY', 'CU'],  # 미국, 북한, 이란, 시리아, 쿠바
        'requires_kyc': False,
        'min_age': 18,
        'vpn_policy': 'warning',  # 'allow', 'warning', 'block'
        'regulation_type': 'decentralized',
        'notes': 'CFTC 규제 이슈로 미국 접근 제한 (2024년 기준)'
    },
    'kalshi': {
        'blocked_countries': ['KP', 'IR', 'SY', 'CU', 'RU'],
        'allowed_countries': ['US'],  # 미국만 허용
        'requires_kyc': True,
        'min_age': 18,
        'vpn_policy': 'block',
        'regulation_type': 'CFTC_regulated',
        'notes': 'CFTC 규제, 미국 거주자만 이용 가능'
    },
    'manifold': {
        'blocked_countries': ['KP', 'IR', 'SY'],
        'requires_kyc': False,
        'min_age': 13,
        'vpn_policy': 'allow',
        'regulation_type': 'play_money',
        'notes': '플레이 머니 기반, 규제 완화'
    }
}

# ===========================
# IP 지오로케이션 서비스
# ===========================

class GeoLocationService:
    """IP 기반 지오로케이션 및 VPN 감지"""

    def __init__(self):
        self.session = None
        self.cache = {}

    async def initialize(self):
        """세션 초기화"""
        self.session = aiohttp.ClientSession()

    async def get_user_location(self, ip_address: Optional[str] = None) -> UserLocation:
        """
        사용자 위치 정보 조회

        여러 서비스를 사용하여 정확도 향상:
        1. ip-api.com (무료, VPN 감지 제한적)
        2. ipapi.co (무료 tier)
        3. IPHub.info (VPN/프록시 감지 전문)
        """

        try:
            # 캐시 확인
            if ip_address in self.cache:
                cached = self.cache[ip_address]
                if (datetime.now() - cached['timestamp']).seconds < 3600:  # 1시간 캐시
                    return cached['data']

            # IP 주소 미지정 시 현재 공인 IP 사용
            if not ip_address:
                ip_address = await self._get_public_ip()

            # 1차: 기본 위치 정보 (ip-api.com)
            location_data = await self._fetch_location_basic(ip_address)

            # 2차: VPN/프록시 감지 (IPHub)
            vpn_data = await self._detect_vpn_proxy(ip_address)

            user_location = UserLocation(
                country=location_data.get('country', 'Unknown'),
                country_code=location_data.get('countryCode', 'XX'),
                region=location_data.get('regionName', 'Unknown'),
                city=location_data.get('city', 'Unknown'),
                ip_address=ip_address,
                is_vpn=vpn_data.get('vpn', False),
                is_proxy=vpn_data.get('proxy', False),
                is_tor=vpn_data.get('tor', False)
            )

            # 캐시 저장
            self.cache[ip_address] = {
                'data': user_location,
                'timestamp': datetime.now()
            }

            return user_location

        except Exception as e:
            logger.error(f"Location detection error: {e}")
            # 기본값 반환 (안전하게 차단)
            return UserLocation(
                country='Unknown',
                country_code='XX',
                region='Unknown',
                city='Unknown',
                ip_address=ip_address or 'Unknown',
                is_vpn=True,  # 알 수 없으면 VPN으로 간주
                is_proxy=True,
                is_tor=False
            )

    async def _get_public_ip(self) -> str:
        """현재 공인 IP 주소 조회"""
        try:
            async with self.session.get('https://api.ipify.org?format=json') as response:
                data = await response.json()
                return data['ip']
        except:
            return '0.0.0.0'

    async def _fetch_location_basic(self, ip_address: str) -> Dict:
        """기본 위치 정보 조회"""
        try:
            url = f'http://ip-api.com/json/{ip_address}'
            async with self.session.get(url, timeout=5) as response:
                return await response.json()
        except Exception as e:
            logger.error(f"Basic location fetch error: {e}")
            return {}

    async def _detect_vpn_proxy(self, ip_address: str) -> Dict:
        """VPN/프록시 감지"""
        try:
            # IPHub API (무료 tier: 1000 requests/day)
            # 실제 사용 시 API 키 필요
            url = f'https://v2.api.iphub.info/ip/{ip_address}'
            headers = {'X-Key': 'YOUR_IPHUB_API_KEY'}  # 환경 변수로 관리 필요

            async with self.session.get(url, headers=headers, timeout=5) as response:
                data = await response.json()

                # IPHub block types:
                # 0 = Residential/Business
                # 1 = VPN/Proxy
                # 2 = TOR
                block_type = data.get('block', 0)

                return {
                    'vpn': block_type == 1,
                    'proxy': block_type == 1,
                    'tor': block_type == 2
                }
        except Exception as e:
            logger.warning(f"VPN detection error: {e}")
            # 감지 실패 시 보수적으로 처리
            return {'vpn': False, 'proxy': False, 'tor': False}

    async def close(self):
        """세션 종료"""
        if self.session:
            await self.session.close()

# ===========================
# 규제 준수 체커
# ===========================

class ComplianceChecker:
    """플랫폼별 규제 준수 검증"""

    def __init__(self, geo_service: GeoLocationService):
        self.geo_service = geo_service
        self.compliance_history = []

    async def check_platform_access(
        self,
        platform: str,
        ip_address: Optional[str] = None,
        user_age: Optional[int] = None,
        kyc_verified: bool = False
    ) -> ComplianceCheck:
        """
        플랫폼 접근 가능 여부 종합 검증

        Args:
            platform: 플랫폼 이름
            ip_address: 사용자 IP (None이면 자동 감지)
            user_age: 사용자 나이
            kyc_verified: KYC 인증 완료 여부
        """

        # 플랫폼 정책 조회
        policy = PLATFORM_RESTRICTIONS.get(platform)
        if not policy:
            return ComplianceCheck(
                platform=platform,
                allowed=False,
                reason=f"Unknown platform: {platform}",
                risk_level='critical',
                restrictions=['Platform not supported'],
                timestamp=datetime.now()
            )

        # 위치 정보 조회
        location = await self.geo_service.get_user_location(ip_address)

        # 검증 실행
        checks = []

        # 1. 지역 제한 체크
        geo_check = self._check_geographic_restrictions(location, policy)
        checks.append(geo_check)

        # 2. VPN/프록시 정책 체크
        vpn_check = self._check_vpn_policy(location, policy)
        checks.append(vpn_check)

        # 3. KYC 요구사항 체크
        kyc_check = self._check_kyc_requirements(kyc_verified, policy)
        checks.append(kyc_check)

        # 4. 연령 제한 체크
        age_check = self._check_age_requirements(user_age, policy)
        checks.append(age_check)

        # 종합 판정
        all_passed = all(check['passed'] for check in checks)
        failed_checks = [c for c in checks if not c['passed']]

        # 리스크 레벨 계산
        risk_level = self._calculate_risk_level(checks, location, policy)

        # 제한 사항 목록
        restrictions = [c['reason'] for c in failed_checks]

        compliance_result = ComplianceCheck(
            platform=platform,
            allowed=all_passed,
            reason=self._format_compliance_reason(checks, location),
            risk_level=risk_level,
            restrictions=restrictions,
            timestamp=datetime.now()
        )

        # 기록 저장
        self.compliance_history.append(compliance_result)

        # 로깅
        if not all_passed:
            logger.warning(
                f"Access denied for {platform}: {compliance_result.reason}"
            )
        else:
            logger.info(
                f"Access granted for {platform} from {location.country_code}"
            )

        return compliance_result

    def _check_geographic_restrictions(
        self,
        location: UserLocation,
        policy: Dict
    ) -> Dict:
        """지역 제한 검증"""

        # 차단 국가 체크
        blocked = policy.get('blocked_countries', [])
        if location.country_code in blocked:
            return {
                'passed': False,
                'reason': f"Country blocked: {location.country} ({location.country_code})",
                'severity': 'critical'
            }

        # 허용 국가 체크 (whitelist 방식)
        allowed = policy.get('allowed_countries', None)
        if allowed and location.country_code not in allowed:
            return {
                'passed': False,
                'reason': f"Country not in allowed list: {location.country}",
                'severity': 'high'
            }

        return {
            'passed': True,
            'reason': f"Geographic check passed: {location.country}",
            'severity': 'none'
        }

    def _check_vpn_policy(self, location: UserLocation, policy: Dict) -> Dict:
        """VPN/프록시 정책 검증"""

        vpn_policy = policy.get('vpn_policy', 'allow')

        # VPN/프록시/TOR 사용 감지
        using_anonymizer = location.is_vpn or location.is_proxy or location.is_tor

        if not using_anonymizer:
            return {
                'passed': True,
                'reason': 'No VPN/proxy detected',
                'severity': 'none'
            }

        # 정책별 처리
        if vpn_policy == 'block':
            return {
                'passed': False,
                'reason': 'VPN/Proxy usage detected and blocked by policy',
                'severity': 'critical'
            }
        elif vpn_policy == 'warning':
            # 경고만 발생, 통과는 허용
            logger.warning(f"VPN/Proxy detected on {policy} - policy: warning")
            return {
                'passed': True,
                'reason': 'VPN/Proxy detected (warning issued)',
                'severity': 'medium'
            }
        else:  # allow
            return {
                'passed': True,
                'reason': 'VPN/Proxy allowed by policy',
                'severity': 'low'
            }

    def _check_kyc_requirements(self, kyc_verified: bool, policy: Dict) -> Dict:
        """KYC 요구사항 검증"""

        requires_kyc = policy.get('requires_kyc', False)

        if requires_kyc and not kyc_verified:
            return {
                'passed': False,
                'reason': 'KYC verification required but not completed',
                'severity': 'high'
            }

        return {
            'passed': True,
            'reason': 'KYC requirements satisfied',
            'severity': 'none'
        }

    def _check_age_requirements(
        self,
        user_age: Optional[int],
        policy: Dict
    ) -> Dict:
        """연령 제한 검증"""

        min_age = policy.get('min_age', 18)

        if user_age is None:
            # 나이 정보 없으면 경고만
            return {
                'passed': True,
                'reason': f'Age verification skipped (minimum: {min_age})',
                'severity': 'low'
            }

        if user_age < min_age:
            return {
                'passed': False,
                'reason': f'User age {user_age} below minimum {min_age}',
                'severity': 'critical'
            }

        return {
            'passed': True,
            'reason': f'Age requirement satisfied ({user_age} >= {min_age})',
            'severity': 'none'
        }

    def _calculate_risk_level(
        self,
        checks: List[Dict],
        location: UserLocation,
        policy: Dict
    ) -> str:
        """종합 리스크 레벨 계산"""

        # 실패한 체크의 severity 수집
        severities = [c['severity'] for c in checks if not c['passed']]

        if 'critical' in severities:
            return 'critical'
        elif 'high' in severities:
            return 'high'
        elif 'medium' in severities:
            return 'medium'
        else:
            # VPN 사용 중이면 최소 low
            if location.is_vpn or location.is_proxy:
                return 'low'
            return 'low'

    def _format_compliance_reason(
        self,
        checks: List[Dict],
        location: UserLocation
    ) -> str:
        """규제 체크 결과 포맷팅"""

        passed = [c['reason'] for c in checks if c['passed']]
        failed = [c['reason'] for c in checks if not c['passed']]

        if failed:
            return f"DENIED: {' | '.join(failed)}"
        else:
            return f"ALLOWED from {location.country} ({location.city})"

    async def check_all_platforms(
        self,
        ip_address: Optional[str] = None,
        user_age: Optional[int] = None,
        kyc_status: Dict[str, bool] = None
    ) -> Dict[str, ComplianceCheck]:
        """모든 플랫폼 동시 검증"""

        if kyc_status is None:
            kyc_status = {}

        results = {}

        for platform in PLATFORM_RESTRICTIONS.keys():
            check = await self.check_platform_access(
                platform=platform,
                ip_address=ip_address,
                user_age=user_age,
                kyc_verified=kyc_status.get(platform, False)
            )
            results[platform] = check

        return results

    def get_compliance_report(self) -> Dict:
        """규제 준수 리포트 생성"""

        if not self.compliance_history:
            return {
                'total_checks': 0,
                'allowed_count': 0,
                'denied_count': 0,
                'risk_distribution': {}
            }

        total = len(self.compliance_history)
        allowed = sum(1 for c in self.compliance_history if c.allowed)
        denied = total - allowed

        # 리스크 분포
        risk_dist = {}
        for check in self.compliance_history:
            risk_dist[check.risk_level] = risk_dist.get(check.risk_level, 0) + 1

        # 플랫폼별 통계
        platform_stats = {}
        for check in self.compliance_history:
            if check.platform not in platform_stats:
                platform_stats[check.platform] = {'allowed': 0, 'denied': 0}

            if check.allowed:
                platform_stats[check.platform]['allowed'] += 1
            else:
                platform_stats[check.platform]['denied'] += 1

        return {
            'total_checks': total,
            'allowed_count': allowed,
            'denied_count': denied,
            'approval_rate': (allowed / total * 100) if total > 0 else 0,
            'risk_distribution': risk_dist,
            'platform_stats': platform_stats,
            'recent_checks': [
                {
                    'platform': c.platform,
                    'allowed': c.allowed,
                    'reason': c.reason,
                    'risk': c.risk_level,
                    'timestamp': c.timestamp.isoformat()
                }
                for c in self.compliance_history[-10:]  # 최근 10개
            ]
        }

# ===========================
# 통합 사용 예시
# ===========================

async def example_usage():
    """규제 준수 체커 사용 예시"""

    # 서비스 초기화
    geo_service = GeoLocationService()
    await geo_service.initialize()

    checker = ComplianceChecker(geo_service)

    # 단일 플랫폼 체크
    print("=" * 60)
    print("Checking Polymarket access...")
    poly_check = await checker.check_platform_access(
        platform='polymarket',
        user_age=25,
        kyc_verified=False
    )
    print(f"Allowed: {poly_check.allowed}")
    print(f"Reason: {poly_check.reason}")
    print(f"Risk Level: {poly_check.risk_level}")

    # 전체 플랫폼 체크
    print("\n" + "=" * 60)
    print("Checking all platforms...")
    all_checks = await checker.check_all_platforms(
        user_age=25,
        kyc_status={'kalshi': True}  # Kalshi만 KYC 완료
    )

    for platform, check in all_checks.items():
        status = "✅" if check.allowed else "❌"
        print(f"{status} {platform.upper()}: {check.reason}")

    # 리포트 생성
    print("\n" + "=" * 60)
    print("Compliance Report:")
    report = checker.get_compliance_report()
    print(f"Total Checks: {report['total_checks']}")
    print(f"Approval Rate: {report['approval_rate']:.1f}%")
    print(f"Risk Distribution: {report['risk_distribution']}")

    # 정리
    await geo_service.close()

if __name__ == "__main__":
    asyncio.run(example_usage())
