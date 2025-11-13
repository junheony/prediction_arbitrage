# Railway 환경 변수 설정

Railway Variables 탭에서 다음 환경 변수를 추가하세요:

## 필수 환경 변수

```bash
# SECRET_KEY 생성 (로컬에서 실행):
# python -c "import secrets; print(secrets.token_hex(32))"

SECRET_KEY=여기에_생성한_긴_문자열_붙여넣기

# 데이터베이스 (SQLite - 파일 기반)
DATABASE_URL=sqlite+aiosqlite:///./arbitrage_bot.db

# 토큰 만료 시간 (7일)
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Kalshi API (최소 하나는 필요)
KALSHI_EMAIL=your_kalshi_email@example.com
KALSHI_PASSWORD=your_kalshi_password

# Opinion API (선택사항)
OPINION_API_KEY=

# Polymarket (선택사항)
POLYMARKET_API_KEY=
POLYMARKET_SECRET=
POLYMARKET_PASSPHRASE=
```

## 주의사항

1. **SECRET_KEY는 반드시 생성해서 사용하세요**
   - 로컬 터미널에서: `python -c "import secrets; print(secrets.token_hex(32))"`
   - 출력된 문자열을 복사해서 Railway에 붙여넣기

2. **KALSHI 크레덴셜은 필수입니다**
   - 봇이 작동하려면 최소 하나의 플랫폼 API가 필요합니다

3. **DATABASE_URL 형식 확인**
   - SQLite: `sqlite+aiosqlite:///./arbitrage_bot.db`
   - PostgreSQL (선택): `postgresql://user:pass@host:5432/dbname`

## Railway에서 변수 추가 방법

1. Railway 프로젝트 → **Variables** 탭
2. **New Variable** 클릭
3. Key와 Value 입력
4. 모든 변수 추가 후 자동 재배포됨

## 확인 방법

배포 후 로그에서 다음 메시지 확인:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:XXXX
```
