# 🚂 Railway 배포 가이드

## ⚠️ 중요: 두 개의 서비스로 분리 배포

Railway는 backend와 frontend를 **별도의 서비스**로 배포해야 합니다.

---

## 방법 1: Railway Dashboard에서 직접 설정 (권장)

### Backend 배포

1. **Railway 프로젝트에서**:
   - "New" → "GitHub Repo" → prediction_arbitrage 선택
   - 또는 기존 배포 수정

2. **Settings → Build 설정**:
   ```
   Root Directory: backend
   Builder: Dockerfile
   Dockerfile Path: ../Dockerfile.backend
   ```

3. **Settings → Deploy 설정**:
   ```
   Start Command: (비워두기, Dockerfile에서 처리)
   Healthcheck Path: /health
   ```

4. **Variables 탭에서 환경 변수 추가**:
   ```
   SECRET_KEY=<생성한 키>
   DATABASE_URL=sqlite:///./arbitrage_bot.db
   KALSHI_EMAIL=your_email
   KALSHI_PASSWORD=your_password
   OPINION_API_KEY=optional
   PORT=8000
   ```

5. **Deploy 클릭**

### Frontend 배포

1. **같은 프로젝트에서 "New Service" 클릭**

2. **기존 GitHub Repo 다시 선택**

3. **Settings → Build 설정**:
   ```
   Root Directory: frontend
   Builder: Nixpacks
   Build Command: npm install && npm run build
   ```

4. **Settings → Deploy 설정**:
   ```
   Start Command: npx serve -s dist -p $PORT
   ```

5. **Variables 탭**:
   ```
   NODE_VERSION=18
   ```

6. **Deploy 클릭**

---

## 방법 2: Render.com 사용 (더 쉬움!)

Railway보다 설정이 간단합니다.

### Backend (Web Service)

1. https://dashboard.render.com → "New +" → "Web Service"

2. **Connect Repository**: prediction_arbitrage 선택

3. **Settings**:
   ```
   Name: prediction-arbitrage-backend
   Root Directory: backend
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

4. **Environment Variables**:
   ```
   SECRET_KEY=<생성>
   DATABASE_URL=sqlite:///./arbitrage_bot.db
   KALSHI_EMAIL=your_email
   KALSHI_PASSWORD=your_password
   PORT=10000
   ```

5. **Create Web Service**

### Frontend (Static Site)

1. "New +" → "Static Site"

2. **Connect Repository**: prediction_arbitrage 선택

3. **Settings**:
   ```
   Name: prediction-arbitrage-frontend
   Root Directory: frontend
   Build Command: npm install && npm run build
   Publish Directory: dist
   ```

4. **Environment Variables**:
   ```
   NODE_VERSION=18
   ```

5. **Create Static Site**

6. **Frontend에서 Backend URL 연결**:
   - Frontend 설정에서 "Redirect/Rewrite" 추가
   - `/api/*` → `https://your-backend.onrender.com/api/*`

---

## 방법 3: 간단한 단일 서버 배포 (통합 버전)

더 간단한 배포를 위해 단일 Dockerfile을 만들겠습니다.

### 파일 생성됨: `Dockerfile.simple`

이 파일로 Railway에 배포:

1. Railway 프로젝트 설정
2. Builder: Dockerfile
3. Dockerfile Path: Dockerfile.simple
4. 환경 변수 추가
5. Deploy!

---

## 🔧 현재 에러 해결

Railway 에러: "Error creating build plan with Railpack"

**원인**: Railway가 root 디렉토리에서 어떤 앱을 빌드해야 할지 모름

**해결책**:

### 옵션 A: Railway에서 Root Directory 설정
1. Railway Dashboard → Settings
2. "Root Directory" → `backend` 입력
3. "Dockerfile Path" → `../Dockerfile.backend` 입력
4. Redeploy

### 옵션 B: 간단한 통합 Dockerfile 사용 (지금 만들겠습니다)

---

## 💡 추천 방법

**Render.com 사용** - Railway보다 설정이 직관적이고 무료 티어도 충분합니다.

또는

**로컬 Docker로 먼저 테스트**:
```bash
# 로컬에서 테스트
docker-compose -f docker-compose.web.yml up --build

# 잘 작동하면 클라우드에 배포
```

---

## 📞 필요한 것

1. **SECRET_KEY 생성**:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **Kalshi 크레덴셜** (필수)
3. **Opinion API Key** (선택사항)

---

## 🚀 다음 단계

1. ✅ Railway 설정 수정 또는 Render.com으로 전환
2. ✅ 환경 변수 입력
3. ✅ 배포 완료!

어떤 방법을 선호하시나요? 지금 바로 진행하겠습니다!
