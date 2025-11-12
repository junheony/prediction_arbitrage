# ☁️ Cloudflare Pages 빠른 설정 가이드

## 🎯 목표
GitHub에서 자동으로 배포되는 랜딩 페이지 만들기

## 1️⃣ Cloudflare 계정 생성 (무료)

1. **Cloudflare 가입**
   - https://dash.cloudflare.com/sign-up
   - 이메일 인증

2. **Dashboard 접속**
   - https://dash.cloudflare.com

## 2️⃣ Pages 프로젝트 생성 (2분)

### Step 1: Workers & Pages 메뉴
1. 좌측 메뉴에서 **"Workers & Pages"** 클릭
2. **"Create application"** 버튼 클릭
3. **"Pages"** 탭 선택
4. **"Connect to Git"** 클릭

### Step 2: GitHub 연결
1. **"Connect GitHub"** 클릭
2. GitHub 로그인 및 권한 부여
3. **"prediction_arbitrage"** 레포지토리 선택
4. **"Begin setup"** 클릭

### Step 3: 빌드 설정
```
Project name: prediction-arbitrage-bot
Production branch: main

Build settings:
├─ Framework preset: None
├─ Build command: (비워두기)
├─ Build output directory: docs
└─ Root directory: (비워두기)
```

### Step 4: 배포
- **"Save and Deploy"** 클릭
- ⏱️ 1-2분 대기
- ✅ 배포 완료!

## 3️⃣ 배포 완료! 🎉

### 자동 생성된 URL
```
https://prediction-arbitrage-bot.pages.dev
```

또는

```
https://prediction-arbitrage-bot-xxx.pages.dev
```

### README 업데이트
이 URL을 README.md에 추가하세요:

```markdown
## 🌐 라이브 데모

**웹사이트**: https://prediction-arbitrage-bot.pages.dev

3개 플랫폼 통합 차익거래 봇의 완전한 문서와 가이드를 확인하세요.
```

## 4️⃣ 자동 배포 설정 완료 ✨

이제 다음이 자동으로 됩니다:

- ✅ `main` 브랜치에 푸시하면 **자동 배포**
- ✅ Pull Request마다 **프리뷰 URL** 생성
- ✅ 전 세계 **CDN 캐싱** (초고속)
- ✅ **무료 SSL** (HTTPS 자동)

## 5️⃣ 커스텀 도메인 (선택사항)

도메인이 있다면:

1. **Pages 프로젝트 > "Custom domains"** 클릭
2. **"Set up a custom domain"** 클릭
3. 도메인 입력 (예: `arbitrage.yourdomain.com`)
4. Cloudflare가 제공하는 DNS 레코드 추가
5. **"Activate domain"** 클릭
6. ⏱️ 5-10분 대기
7. ✅ HTTPS 자동 활성화!

## 6️⃣ 테스트

### 로컬에서 변경
```bash
# docs/index.html 수정
nano docs/index.html

# 커밋 및 푸시
git add docs/index.html
git commit -m "📝 Update landing page"
git push origin main
```

### 자동 배포 확인
1. Cloudflare Dashboard > Pages > prediction-arbitrage-bot
2. "Deployments" 탭
3. 진행 상황 확인 (1-2분)
4. 배포 완료 후 URL 방문

## 7️⃣ 성능

Cloudflare Pages의 장점:

- ⚡ **전 세계 CDN**: 200+ 도시에서 캐싱
- 🔒 **무료 SSL**: Let's Encrypt 자동 갱신
- 🚀 **빠른 배포**: 1-2분 이내
- 💰 **무료**: 무제한 요청
- 📊 **Analytics**: 무료 트래픽 분석

## 8️⃣ 문제 해결

### 빌드 실패
```
Error: Could not find build output directory
```
**해결:**
- Build output directory가 `docs`로 설정되었는지 확인
- `docs/index.html` 파일 존재 확인

### 404 에러
```
Page not found
```
**해결:**
- `docs/index.html` 파일명 확인
- 대소문자 확인 (index.html, 소문자)

### 자동 배포 안 됨
**해결:**
1. Cloudflare Dashboard > Settings > Git integration
2. GitHub 연결 상태 확인
3. "Re-authenticate with GitHub" 클릭

## 9️⃣ 추가 설정 (고급)

### Analytics 활성화
1. Pages 프로젝트 > "Analytics" 탭
2. 자동으로 트래픽 통계 수집
3. 무료!

### Redirects 설정
`docs/_redirects` 파일 생성:
```
/github  https://github.com/junheony/prediction_arbitrage  301
/docs    https://github.com/junheony/prediction_arbitrage/blob/main/prediction_arbitrage/THREE_PLATFORMS_GUIDE.md  301
```

### Custom Headers
`docs/_headers` 파일 생성:
```
/*
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Cache-Control: public, max-age=3600
```

## 🔟 완료 체크리스트

- [x] Cloudflare 계정 생성
- [x] Pages 프로젝트 생성
- [x] GitHub 연결
- [x] 빌드 설정
- [x] 배포 완료
- [x] URL 확인
- [ ] README에 URL 추가
- [ ] (선택) 커스텀 도메인 설정
- [ ] (선택) Analytics 활성화

## 📱 공유하기

배포 완료! 이제 이 URL을 공유하세요:

```
🌐 https://prediction-arbitrage-bot.pages.dev
```

**소셜 미디어:**
```
🎉 3개 플랫폼 통합 예측시장 차익거래 봇 완성!

Polymarket + Kalshi + Opinion.trade
실시간 WebSocket, +300% 기회, -90% 레이턴시

🔗 https://prediction-arbitrage-bot.pages.dev
⭐ https://github.com/junheony/prediction_arbitrage

#crypto #arbitrage #trading #python #opensource
```

---

## ✅ 완료!

**라이브 사이트**: https://prediction-arbitrage-bot.pages.dev

모든 변경사항이 자동으로 배포됩니다! 🚀
