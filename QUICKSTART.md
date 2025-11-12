# 🚀 빠른 시작 가이드

## 5분 안에 시작하기

### 1단계: 설치 (1분)

```bash
# 저장소 클론
cd prediction_arbitrage

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2단계: 환경 설정 (2분)

```bash
# .env 파일 생성
cp .env.template .env

# .env 파일 편집
nano .env  # 또는 원하는 에디터 사용
```

**최소 설정 (.env):**
```bash
# Polymarket (공개 데이터만 사용 시 불필요)
# POLYMARKET_PRIVATE_KEY=your_key

# Kalshi (크레덴셜 필요)
KALSHI_EMAIL=your@email.com
KALSHI_PASSWORD=your_password

# Opinion (선택사항)
OPINION_API_KEY=your_api_key
```

### 3단계: 실행 (1분)

```bash
python integrated_bot.py
```

**출력:**
```
╔══════════════════════════════════════════════════════════════╗
║      🤖 INTEGRATED PREDICTION ARBITRAGE BOT 🤖              ║
║                   3-Platform Support                         ║
║  📊 Platforms:                                               ║
║     • Polymarket (WebSocket + REST)                          ║
║     • Kalshi (WebSocket + REST)                              ║
║     • Opinion.trade (WebSocket + REST)                       ║
╚══════════════════════════════════════════════════════════════╝

🚀 Initializing Integrated Arbitrage Bot...
✅ POLYMARKET: Access granted
✅ KALSHI: Access granted
✅ OPINION: Access granted
🟢 Bot started - monitoring for opportunities...

📊 Scanning for arbitrage opportunities across all platforms...
  Polymarket: 10 markets
  Kalshi: 8 markets
  Opinion: 5 markets
```

## 개별 플랫폼 테스트

### Polymarket 테스트
```bash
python polymarket_websocket.py
```

### Kalshi 테스트
```bash
python kalshi_client.py
```

### Opinion 테스트
```bash
python opinion_client.py
```

## 설정 커스터마이징

**[integrated_bot.py](integrated_bot.py)** 파일 내 config 수정:

```python
config = {
    # 플랫폼 크레덴셜
    'kalshi_email': 'your@email.com',
    'kalshi_password': 'your_password',
    'opinion_api_key': 'your_api_key',  # 선택사항

    # 거래 파라미터
    'min_roi': 2.0,  # 최소 2% 수익률
    'min_gap': 1.5,  # 최소 1.5% 가격 갭
    'max_slippage': 1.0,  # 최대 1% 슬리피지
    'base_position_size': 10000,  # $10,000 포지션

    # 리스크 관리
    'hedge_profit_threshold': 50.0,  # $50 이상 시 헤지
    'hedge_loss_threshold': -20.0,   # -$20 손실 시 헤지
    'min_match_score': 0.75,  # 75% 이상 매칭만 허용

    # 알림 (선택사항)
    'slack_webhook': None,
    'telegram_bot_token': None,
    'telegram_chat_id': None
}
```

## 필수 계정 생성

### Kalshi (필수)
1. https://kalshi.com 방문
2. 회원가입
3. **KYC 인증 완료** (미국 거주자만)
4. 이메일/비밀번호를 .env에 입력

### Opinion.trade (선택사항)
1. https://opinion.trade 방문
2. 지갑 연결
3. API 키 생성 (Settings > API Keys)
4. API 키를 .env에 입력

### Polymarket (거래 시 필요)
1. MetaMask 설치
2. Polygon 네트워크 추가
3. USDC 준비
4. Private Key를 .env에 입력 (읽기 전용은 불필요)

## 차익거래 예시

봇이 자동으로 이런 기회를 찾습니다:

```
📊 Opportunity Found!

Market: "Will Bitcoin reach $100k by 2025?"
├─ Polymarket: YES 65¢, NO 35¢
├─ Kalshi: YES 60¢, NO 38¢
└─ Opinion: YES 62¢, NO 36¢

💡 Strategy: Buy Kalshi NO + Sell Polymarket YES
├─ Cost: 38¢ + 35¢ = 73¢
├─ Payout: $1.00 (guaranteed)
├─ Gross Profit: 27¢
├─ Fees: Kalshi 0.7% (~0.27¢)
└─ Net Profit: 26.73¢ (36.6% ROI)

🎯 Executing trade...
```

## 문제 해결

### Kalshi 로그인 실패
```bash
❌ Kalshi login failed
```
→ 이메일/비밀번호 확인, KYC 완료 여부 체크

### WebSocket 연결 실패
```bash
❌ WebSocket connection failed
```
→ 인터넷 연결 확인, 방화벽 설정 확인

### 토큰 만료 에러
```bash
❌ Token expired
```
→ 봇 재시작 (자동 갱신되어야 하지만 수동 재시작 필요할 수 있음)

## 다음 단계

- 📖 [상세 문서](THREE_PLATFORMS_GUIDE.md) 읽기
- 🔧 [구현 가이드](IMPLEMENTATION_GUIDE.md) 확인
- 💡 [프로젝트 가이드](PROJECT_GUIDE.md) 참고

## 주의사항

⚠️ **소액으로 먼저 테스트하세요!**
- 첫 거래는 $100 이하로 시작
- 규제 요구사항 확인
- 수수료 계산 검증

🔒 **보안 주의:**
- `.env` 파일을 절대 공유하지 마세요
- Private Key는 안전하게 보관
- VPN 사용 시 플랫폼 정책 확인

📊 **성능 모니터링:**
- 로그 파일 확인: `arbitrage_bot.log`
- 실시간 통계: 터미널 출력
- 알림 설정: Slack/Telegram 연동

---

**준비 완료!** 이제 차익거래를 시작할 수 있습니다 🚀
