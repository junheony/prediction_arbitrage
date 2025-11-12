# 🌐 Prediction Arbitrage Bot - Web Application

## 🎉 새로운 기능: 웹 애플리케이션!

이제 웹 브라우저에서 로그인하여 차익거래 봇을 제어할 수 있습니다!

---

## ✨ 주요 기능

### 🔐 사용자 인증
- 이메일/비밀번호 회원가입
- JWT 토큰 기반 로그인
- 안전한 세션 관리

### 🤖 봇 제어
- 웹 UI에서 봇 시작/중지
- 실시간 상태 모니터링
- 설정 커스터마이징:
  - 최소 수익률 임계값
  - 최대 포지션 크기
  - 플랫폼 선택 (Polymarket, Kalshi, Opinion)
  - 자동 실행 옵션

### 📊 실시간 대시보드
- 봇 상태 (실행중/중지)
- 발견된 기회 수
- 총 잠재 수익
- 실시간 WebSocket 업데이트

### 💰 차익거래 기회 목록
- 실시간 기회 표시
- 플랫폼별 필터링
- 수익률 정렬
- 제안된 액션 표시

---

## 🚀 빠른 시작

### 로컬 개발 환경

#### 1. 백엔드 실행

```bash
cd backend

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일을 편집하여 API 크레덴셜 입력

# 서버 실행
python main.py
```

백엔드: http://localhost:8000
API 문서: http://localhost:8000/docs

#### 2. 프론트엔드 실행

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

프론트엔드: http://localhost:3000

#### 3. 계정 생성 및 사용

1. http://localhost:3000 접속
2. "Sign up" 클릭하여 회원가입
3. 로그인
4. 대시보드에서 봇 설정 및 시작!

---

## 🐳 Docker로 배포

```bash
# 환경 변수 설정
cp .env.production .env
nano .env  # API 크레덴셜 입력

# Docker Compose로 실행
docker-compose up --build

# 백그라운드 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 중지
docker-compose down
```

접속: http://localhost:3000

---

## ☁️ 클라우드 배포

### Railway.app (추천)

1. https://railway.app 회원가입
2. "New Project" → GitHub 연결
3. 백엔드/프론트엔드 각각 배포
4. 환경 변수 설정
5. 완료!

자세한 가이드: [WEB_APP_SETUP.md](WEB_APP_SETUP.md)

### 다른 옵션
- Render.com
- DigitalOcean
- AWS / GCP
- Heroku

---

## 🏗️ 기술 스택

### Backend
- **FastAPI** - 고성능 Python 웹 프레임워크
- **SQLAlchemy** - ORM
- **JWT** - 인증
- **WebSockets** - 실시간 통신
- **SQLite/PostgreSQL** - 데이터베이스

### Frontend
- **React 18** - UI 라이브러리
- **Vite** - 빌드 도구
- **Tailwind CSS** - 스타일링
- **Axios** - HTTP 클라이언트
- **React Router** - 라우팅

---

## 📱 스크린샷

### 로그인 화면
- 깔끔한 그라데이션 디자인
- 이메일/비밀번호 로그인
- 회원가입 링크

### 대시보드
- 3개 통계 카드 (상태, 기회, 수익)
- 봇 제어 패널 (시작/중지/설정)
- 실시간 기회 목록

### 봇 설정
- 플랫폼 선택 (체크박스)
- 최소 수익률 슬라이더
- 최대 포지션 크기 슬라이더
- 자동 실행 옵션

---

## 🔐 보안

- JWT 토큰 기반 인증
- 비밀번호 해싱 (bcrypt)
- CORS 보호
- 환경 변수로 크레덴셜 관리
- HTTPS 지원 (프로덕션)

---

## 📊 API 엔드포인트

```
POST /api/auth/register     - 회원가입
POST /api/auth/login        - 로그인
GET  /api/auth/me           - 현재 사용자 정보

POST /api/bot/start         - 봇 시작
POST /api/bot/stop          - 봇 중지
GET  /api/bot/status        - 봇 상태 조회
GET  /api/bot/opportunities - 기회 목록

WS   /ws?token=<jwt>        - WebSocket 연결
```

전체 문서: http://localhost:8000/docs

---

## 🎯 주요 특징

### 다중 사용자 지원
- 각 사용자는 독립적인 봇 인스턴스
- 개별 기회 추적
- 개인별 설정 저장

### 실시간 업데이트
- WebSocket으로 즉각적인 기회 알림
- 봇 상태 실시간 동기화
- 연결 끊김 자동 재연결

### 반응형 디자인
- 모바일/태블릿/데스크톱 지원
- Tailwind CSS로 현대적인 UI
- 다크/라이트 테마 (향후 추가 예정)

---

## 🚧 향후 계획

- [ ] 실제 주문 실행 기능
- [ ] 이메일/Slack 알림
- [ ] 차트 및 히스토리 분석
- [ ] 백테스팅 시스템
- [ ] 관리자 대시보드
- [ ] API 사용량 제한
- [ ] 소셜 로그인 (Google, GitHub)

---

## 📚 문서

- [WEB_APP_SETUP.md](WEB_APP_SETUP.md) - 상세 설정 가이드
- [THREE_PLATFORMS_GUIDE.md](prediction_arbitrage/THREE_PLATFORMS_GUIDE.md) - 플랫폼 가이드
- [QUICKSTART.md](prediction_arbitrage/QUICKSTART.md) - 빠른 시작
- [API 문서](http://localhost:8000/docs) - Swagger UI

---

## 🐛 트러블슈팅

### 백엔드 실행 오류
```bash
# 포트 확인
lsof -i :8000

# 가상환경 재생성
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 프론트엔드 실행 오류
```bash
# node_modules 재설치
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### WebSocket 연결 오류
1. 백엔드가 실행 중인지 확인
2. 브라우저 콘솔에서 토큰 확인
3. CORS 설정 확인

---

## 🤝 기여

1. Fork 프로젝트
2. Feature 브랜치 생성
3. 변경사항 커밋
4. 브랜치에 Push
5. Pull Request 생성

---

## 📄 라이선스

MIT License

---

## 🌟 주요 개선사항

### v2.0 → v3.0
- ✅ **웹 애플리케이션 추가**
- ✅ 사용자 인증 시스템
- ✅ 실시간 WebSocket 통신
- ✅ 반응형 대시보드
- ✅ Docker 배포 지원
- ✅ 클라우드 배포 가이드

---

**이제 친구들과 함께 웹에서 차익거래 봇을 사용하세요! 🚀**

로컬 개발: `WEB_APP_SETUP.md` 참고
배포: Railway.app 또는 Render.com 추천

Happy Trading! 💰📈
