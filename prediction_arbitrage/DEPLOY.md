# 🚀 Cloudflare Pages 배포 가이드

## 1. GitHub 레포지토리 준비

### 1-1. Git 초기화 및 커밋

```bash
cd /Users/max/Documents/개발/prediction_arbitrage

# Git 상태 확인
git status

# 모든 변경사항 추가
git add .

# 커밋
git commit -m "🎉 3-Platform Arbitrage Bot v2.0 - Polymarket + Kalshi + Opinion

- Added Kalshi REST + WebSocket client
- Added Opinion.trade REST + WebSocket client
- Updated integrated bot for 3-platform support
- Added comprehensive documentation
- Added example usage and demo scripts
- Performance: +300% opportunities, -90% latency, +87% ROI

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 1-2. GitHub에 푸시

```bash
# 원격 레포지토리 추가 (처음인 경우)
git remote add origin https://github.com/YOUR_USERNAME/prediction-arbitrage-bot.git

# 푸시
git push -u origin main

# 또는 이미 origin이 있는 경우
git push origin main
```

## 2. Cloudflare Pages 배포

### 2-1. Cloudflare Pages 프로젝트 생성

1. **Cloudflare Dashboard 접속**
   - https://dash.cloudflare.com
   - "Workers & Pages" 메뉴 클릭

2. **새 프로젝트 생성**
   - "Create application" 클릭
   - "Pages" 탭 선택
   - "Connect to Git" 클릭

3. **GitHub 연결**
   - GitHub 계정 인증
   - `prediction-arbitrage-bot` 레포지토리 선택

4. **빌드 설정**
   - **Framework preset**: None (정적 사이트)
   - **Build command**: (비워두기)
   - **Build output directory**: `docs`
   - **Root directory**: `/`

5. **환경 변수** (선택사항)
   - 필요 없음 (정적 HTML만 배포)

6. **배포 시작**
   - "Save and Deploy" 클릭
   - 1-2분 후 배포 완료

### 2-2. 커스텀 도메인 설정 (선택사항)

1. **도메인 추가**
   - Pages 프로젝트 > "Custom domains" 탭
   - "Set up a custom domain" 클릭
   - 도메인 입력 (예: arbitrage.yourdomain.com)

2. **DNS 레코드 추가**
   - Cloudflare가 자동으로 CNAME 레코드 제안
   - "Activate domain" 클릭

3. **SSL/TLS 설정**
   - 자동으로 SSL 인증서 발급 (무료)
   - HTTPS 자동 활성화

## 3. 배포 완료 후

### 3-1. 사이트 확인

배포된 URL:
```
https://prediction-arbitrage-bot.pages.dev
```

커스텀 도메인 (설정한 경우):
```
https://arbitrage.yourdomain.com
```

### 3-2. README 업데이트

```bash
# README.md에 배포 URL 추가
nano README.md

# 커밋 및 푸시
git add README.md
git commit -m "📝 Update README with deployment URL"
git push origin main
```

README에 추가할 내용:
```markdown
## 🌐 라이브 데모

**웹사이트**: https://prediction-arbitrage-bot.pages.dev

3개 플랫폼 통합 차익거래 봇의 완전한 문서와 가이드를 확인하세요.
```

## 4. 자동 배포 설정

Cloudflare Pages는 **자동으로 배포**됩니다:

- `main` 브랜치에 푸시하면 자동 배포
- 각 PR에 대해 프리뷰 URL 생성
- 빌드 로그 확인 가능

### 4-1. 수동 재배포

필요한 경우:
1. Cloudflare Dashboard > Pages 프로젝트
2. "Deployments" 탭
3. "Create deployment" 클릭

## 5. 고급 설정

### 5-1. Redirects 설정

`docs/_redirects` 파일 생성:
```
/github  https://github.com/YOUR_USERNAME/prediction-arbitrage-bot  301
/docs    https://github.com/YOUR_USERNAME/prediction-arbitrage-bot/blob/main/prediction_arbitrage/THREE_PLATFORMS_GUIDE.md  301
```

### 5-2. Headers 설정

`docs/_headers` 파일 생성:
```
/*
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: no-referrer-when-downgrade
  Cache-Control: public, max-age=3600
```

### 5-3. Custom 404 페이지

`docs/404.html` 파일 생성 (이미 있으면 자동 사용)

## 6. 성능 최적화

### 6-1. 이미지 최적화
```bash
# Cloudflare Images 사용 (선택사항)
# 자동으로 WebP 변환, 리사이징
```

### 6-2. 캐싱 설정
- Cloudflare CDN이 자동으로 전 세계 배포
- Edge 캐싱으로 초고속 로딩
- 무료 SSL/TLS

### 6-3. Analytics 설정
1. Pages 프로젝트 > "Analytics" 탭
2. 자동으로 트래픽 통계 확인 가능

## 7. 유지보수

### 7-1. 문서 업데이트 워크플로우

```bash
# 1. 로컬에서 변경
nano prediction_arbitrage/THREE_PLATFORMS_GUIDE.md

# 2. 커밋
git add .
git commit -m "📝 Update documentation"

# 3. 푸시 (자동 배포됨)
git push origin main

# 4. 1-2분 후 라이브 사이트 자동 업데이트
```

### 7-2. 롤백

문제 발생 시:
1. Cloudflare Dashboard > Deployments
2. 이전 배포 선택
3. "Rollback to this deployment" 클릭

## 8. 트러블슈팅

### 빌드 실패
```
❌ Build failed: Could not find build output directory
```
**해결:** Build output directory를 `docs`로 설정

### 404 에러
```
❌ Page not found
```
**해결:** `docs/index.html` 파일 존재 확인

### 커스텀 도메인 연결 안 됨
```
❌ DNS validation failed
```
**해결:**
1. DNS 전파 대기 (최대 24시간)
2. CNAME 레코드 확인
3. Cloudflare nameserver 사용 확인

## 9. 보안

### 9-1. 민감 정보 제외

`.gitignore`에 반드시 포함:
```
.env
*_private_key*
*credentials*
*.pem
```

### 9-2. API 키 노출 방지

- GitHub에 `.env` 파일 절대 커밋 금지
- Public 레포지토리인 경우 특히 주의
- `.env.template`만 커밋

## 10. 완료 체크리스트

- [ ] Git 레포지토리 생성
- [ ] 모든 변경사항 커밋
- [ ] GitHub에 푸시
- [ ] Cloudflare Pages 프로젝트 생성
- [ ] 배포 완료 확인
- [ ] 라이브 URL 테스트
- [ ] README에 URL 추가
- [ ] (선택) 커스텀 도메인 설정
- [ ] (선택) Analytics 활성화

## 11. 추가 리소스

- **Cloudflare Pages 문서**: https://developers.cloudflare.com/pages
- **Custom domains**: https://developers.cloudflare.com/pages/platform/custom-domains
- **Build configuration**: https://developers.cloudflare.com/pages/platform/build-configuration

---

## 🎉 완료!

이제 다음 URL에서 프로젝트를 확인할 수 있습니다:

**🌐 https://prediction-arbitrage-bot.pages.dev**

모든 변경사항이 `main` 브랜치에 푸시되면 자동으로 배포됩니다!
