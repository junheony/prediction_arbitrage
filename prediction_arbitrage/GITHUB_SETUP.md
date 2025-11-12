# 📦 GitHub 레포지토리 설정 가이드

## 1. GitHub 레포지토리 생성

### 옵션 A: GitHub 웹사이트에서 생성

1. **GitHub 접속**
   - https://github.com 로그인

2. **새 레포지토리 생성**
   - 우측 상단 "+" 버튼 클릭
   - "New repository" 선택

3. **레포지토리 설정**
   ```
   Repository name: prediction-arbitrage-bot
   Description: 세계 최초 3개 플랫폼 통합 무위험 차익거래 봇 - Polymarket + Kalshi + Opinion.trade

   Public ✅ (또는 Private)

   ✅ Add a README file (건너뛰기 - 이미 있음)
   ✅ Add .gitignore → Python
   ✅ Choose a license → MIT License
   ```

4. **"Create repository" 클릭**

### 옵션 B: GitHub CLI 사용

```bash
# GitHub CLI 설치 (Mac)
brew install gh

# 인증
gh auth login

# 레포지토리 생성
gh repo create prediction-arbitrage-bot \
  --public \
  --description "세계 최초 3개 플랫폼 통합 무위험 차익거래 봇" \
  --source=. \
  --remote=origin \
  --push
```

## 2. 로컬 레포지토리 연결

### 2-1. Git 원격 저장소 설정

```bash
cd /Users/max/Documents/개발/prediction_arbitrage

# 원격 저장소 추가
git remote add origin https://github.com/YOUR_USERNAME/prediction-arbitrage-bot.git

# 원격 저장소 확인
git remote -v
```

**YOUR_USERNAME을 실제 GitHub 사용자명으로 변경하세요!**

### 2-2. 첫 푸시

```bash
# main 브랜치로 푸시
git push -u origin main

# 또는 master 브랜치인 경우
git branch -M main
git push -u origin main
```

## 3. GitHub 레포지토리 설정

### 3-1. Repository Settings

**About 섹션 설정:**
```
Description:
세계 최초 3개 플랫폼 통합 무위험 차익거래 봇 - Polymarket, Kalshi, Opinion.trade

Website:
https://prediction-arbitrage-bot.pages.dev

Topics:
arbitrage, prediction-markets, polymarket, kalshi, opinion-trade,
cryptocurrency, trading-bot, websocket, python, real-time
```

### 3-2. Branch Protection Rules (선택사항)

Settings > Branches > Add rule:
```
Branch name pattern: main

✅ Require pull request reviews before merging
✅ Require status checks to pass before merging
✅ Require branches to be up to date before merging
```

### 3-3. GitHub Pages 비활성화

Settings > Pages:
```
Source: None

(Cloudflare Pages를 사용하므로 GitHub Pages는 불필요)
```

## 4. README 배지 추가

`README.md` 상단에 추가:

```markdown
# 🤖 Web3 예측시장 무위험 차익거래 봇

**3개 플랫폼 통합 지원: Polymarket + Kalshi + Opinion.trade**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platforms](https://img.shields.io/badge/Platforms-3-success.svg)]()
[![GitHub Stars](https://img.shields.io/github/stars/YOUR_USERNAME/prediction-arbitrage-bot?style=social)](https://github.com/YOUR_USERNAME/prediction-arbitrage-bot)
[![Website](https://img.shields.io/badge/Website-Live-brightgreen)](https://prediction-arbitrage-bot.pages.dev)

🌐 **라이브 데모**: [https://prediction-arbitrage-bot.pages.dev](https://prediction-arbitrage-bot.pages.dev)
```

커밋 및 푸시:
```bash
git add README.md
git commit -m "📝 Add badges and live demo link"
git push origin main
```

## 5. 문서 구조 확인

레포지토리에 다음 파일들이 있는지 확인:

```
prediction-arbitrage-bot/
├── README.md                          ✅ 메인 소개
├── LICENSE                            ✅ MIT 라이선스
├── .gitignore                         ✅ 제외 파일 목록
├── DEPLOY.md                          ✅ 배포 가이드
├── GITHUB_SETUP.md                    ✅ 이 파일
│
├── docs/
│   └── index.html                     ✅ 랜딩 페이지
│
├── prediction_arbitrage/
│   ├── integrated_bot.py              ✅ 메인 봇
│   ├── kalshi_client.py               ✅ Kalshi 클라이언트
│   ├── opinion_client.py              ✅ Opinion 클라이언트
│   ├── example_usage.py               ✅ 예제 코드
│   ├── run_demo.sh                    ✅ 데모 스크립트
│   │
│   ├── QUICKSTART.md                  ✅ 빠른 시작
│   ├── THREE_PLATFORMS_GUIDE.md       ✅ 3-플랫폼 가이드
│   ├── IMPLEMENTATION_GUIDE.md        ✅ 구현 가이드
│   ├── SUMMARY.md                     ✅ 프로젝트 요약
│   ├── CHANGELOG.md                   ✅ 변경 이력
│   └── .env.template                  ✅ 환경 변수 템플릿
│
└── requirements.txt                   ✅ 의존성
```

## 6. Issue Templates 생성 (선택사항)

`.github/ISSUE_TEMPLATE/bug_report.md`:
```markdown
---
name: Bug Report
about: 버그 리포트
title: '[BUG] '
labels: bug
---

**버그 설명**
명확하고 간결한 버그 설명

**재현 방법**
1. '...'로 이동
2. '...'를 클릭
3. '...'를 스크롤
4. 에러 확인

**예상 동작**
예상했던 동작 설명

**스크린샷**
해당되는 경우 스크린샷 추가

**환경:**
- OS: [e.g. macOS 14.0]
- Python: [e.g. 3.11]
- 플랫폼: [e.g. Kalshi]

**추가 컨텍스트**
추가 정보
```

`.github/ISSUE_TEMPLATE/feature_request.md`:
```markdown
---
name: Feature Request
about: 기능 제안
title: '[FEATURE] '
labels: enhancement
---

**기능 설명**
원하는 기능에 대한 명확하고 간결한 설명

**문제점**
이 기능이 해결할 문제점

**제안 솔루션**
원하는 동작 설명

**대안**
고려한 다른 대안들

**추가 컨텍스트**
추가 정보 또는 스크린샷
```

## 7. GitHub Actions (선택사항)

`.github/workflows/test.yml`:
```yaml
name: Tests

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Lint with flake8
      run: |
        pip install flake8
        flake8 prediction_arbitrage --count --select=E9,F63,F7,F82 --show-source --statistics
```

## 8. 푸시 및 확인

```bash
# 모든 변경사항 푸시
git add .
git commit -m "📝 Add GitHub setup documentation and templates"
git push origin main

# GitHub에서 확인
# https://github.com/YOUR_USERNAME/prediction-arbitrage-bot
```

## 9. 다음 단계

✅ **완료된 작업:**
- [x] GitHub 레포지토리 생성
- [x] 로컬 레포지토리 연결
- [x] 첫 커밋 및 푸시
- [x] README 업데이트
- [x] 문서 구조 확인

📋 **다음 할 일:**
- [ ] Cloudflare Pages 배포 (DEPLOY.md 참고)
- [ ] 커스텀 도메인 설정 (선택사항)
- [ ] GitHub Stars 홍보
- [ ] 커뮤니티에 공유

## 10. 유용한 Git 명령어

```bash
# 상태 확인
git status

# 변경사항 확인
git diff

# 커밋 이력
git log --oneline --graph --all

# 원격 저장소 확인
git remote -v

# 브랜치 확인
git branch -a

# 최신 변경사항 가져오기
git pull origin main

# 특정 파일 되돌리기
git checkout -- file.py
```

## 11. 트러블슈팅

### 원격 저장소 이미 존재
```bash
fatal: remote origin already exists
```
**해결:**
```bash
git remote rm origin
git remote add origin https://github.com/YOUR_USERNAME/prediction-arbitrage-bot.git
```

### 인증 실패
```bash
fatal: Authentication failed
```
**해결:**
1. Personal Access Token 생성: https://github.com/settings/tokens
2. 토큰으로 로그인

### 푸시 거부됨
```bash
! [rejected] main -> main (fetch first)
```
**해결:**
```bash
git pull origin main --rebase
git push origin main
```

---

## ✅ 완료!

이제 GitHub 레포지토리가 준비되었습니다!

**다음 단계:** [DEPLOY.md](DEPLOY.md)를 참고하여 Cloudflare Pages에 배포하세요.
