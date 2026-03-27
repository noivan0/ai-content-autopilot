# ai-content-autopilot

> **Claude AI 기반 콘텐츠 자동화 파이프라인**  
> Blog · X · Instagram · YouTube Shorts · Newsletter — Research → SEO → Write → Publish 원클릭

---

## 개요

Claude AI를 활용해 매일 AI 관련 콘텐츠를 자동으로 생성하고 Blog, X, Instagram, YouTube Shorts, 뉴스레터까지 한 번에 배포하는 시스템입니다.  
SEO 최적화, E-E-A-T 기반 고품질 콘텐츠 생성, 멀티채널 자동 배포를 완전히 자동화합니다.

```
[매일 06:00 KST]
Research → SEO → Writer → Image → Publisher
                                      ↓
                             SNS (Instagram / X / YouTube)
                             Newsletter
```

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| **리서치 자동화** | Brave Search + arXiv + GitHub 트렌드로 당일 핫토픽 3개 자동 선정 |
| **SEO 최적화** | 키워드 분석, 검색 의도 파악, H1~H3 구조 설계, 메타 디스크립션 자동 생성 |
| **고품질 작성** | Claude API로 3,000자+ 포스트, FAQ Schema, ToC, 핵심 요약 박스 포함 |
| **이미지 생성** | Pillow로 썸네일 + SNS 카드 이미지 자동 생성 |
| **자동 발행** | Google Blogger API v3 연동, 라벨/예약 포스팅 지원 |
| **SNS 배포** | X(Twitter) 스레드, Instagram 카드, YouTube Shorts, 주간 뉴스레터 |
| **SEO 검증** | 발행 전 H1/ToC/FAQ Schema/JSON-LD/내외부 링크 자동 검증 |

---

## 디렉토리 구조

```
ai-blog-autopilot/
├── run_daily.py                 # 메인 실행 스크립트
├── setup_oauth.py               # Google OAuth2 초기 인증
├── .env.example                 # 환경변수 템플릿
├── agents/
│   ├── research.py              # 리서치 에이전트 (Brave Search + arXiv)
│   ├── seo.py                   # SEO 에이전트 (키워드 + 구조 설계)
│   ├── writer.py                # 작성 에이전트 (Claude API)
│   ├── image_gen.py             # 이미지 생성 에이전트 (Pillow)
│   ├── publisher.py             # 발행 에이전트 (Blogger API)
│   ├── analytics.py             # 성과 분석 (Search Console)
│   ├── sns_pipeline.py          # SNS 변환 + 배포 조율
│   ├── converters/              # 포맷 변환기
│   │   ├── thread_converter.py  # X 스레드 변환
│   │   ├── card_converter.py    # Instagram 카드 변환
│   │   ├── newsletter_converter.py # 뉴스레터 변환
│   │   └── shorts_converter.py  # YouTube Shorts 변환
│   └── distributors/            # SNS 배포기
│       ├── x_bot.py
│       ├── instagram_bot.py
│       └── youtube_bot.py
├── templates/
│   ├── post_template.html       # Blogger 포스트 HTML 템플릿
│   ├── blogger_theme_optimized.xml # Blogger 테마 (SEO 최적화)
│   └── seo_checklist.md        # SEO 체크리스트
├── scripts/
│   └── download_fonts.py        # 한글 폰트 다운로드
├── assets/
│   └── fonts/                   # NotoSansKR (이미지 생성용)
└── output/                      # 생성 결과물 (gitignore 일부)
    ├── topics/                  # 리서치 결과
    ├── seo/                     # SEO 계획
    ├── posts/                   # 작성된 HTML 포스트
    ├── images/                  # 썸네일 + SNS 카드
    ├── threads/                 # X 스레드 JSON
    ├── newsletters/             # 주간 뉴스레터 HTML
    └── logs/                    # 실행 로그 + SEO 검증 결과
```

---

## 빠른 시작

### 1. 클론 & 환경 설정

```bash
git clone https://github.com/your-username/ai-blog-autopilot.git
cd ai-blog-autopilot

# 환경변수 설정
cp .env.example .env
# .env 파일을 열어 API 키 입력
```

### 2. 의존성 설치

```bash
# Python 3.10+ 권장, 외부 패키지 없음 (표준 라이브러리만 사용)
# 이미지 생성 기능 사용 시
pip install pillow

# YouTube Shorts 생성 시
# ffmpeg 별도 설치 필요: https://ffmpeg.org/download.html
```

### 3. Google OAuth2 인증 (Blogger 발행 시 필요)

```bash
python setup_oauth.py
# 브라우저 열림 → Google 계정 인증 → refresh_token 자동 저장
```

### 4. 실행

```bash
# 전체 파이프라인 (발행 포함)
python run_daily.py

# 발행 없이 콘텐츠만 생성
python run_daily.py --no-publish

# 더미 리서치 데이터로 테스트 (Brave API 없이)
python run_daily.py --mock-research --no-publish
```

---

## 필요 API 키

| API | 용도 | 무료 여부 |
|-----|------|-----------|
| [Anthropic Claude](https://console.anthropic.com/) | 콘텐츠 생성 (필수) | 유료 |
| [Brave Search API](https://api.search.brave.com/) | 리서치 (필수) | 무료 플랜 있음 |
| [Google Blogger API](https://developers.google.com/blogger) | 자동 발행 | 무료 |
| [Google Search Console API](https://search.google.com/search-console) | 성과 분석 | 무료 |
| [ImgBB API](https://api.imgbb.com/) | SNS용 이미지 호스팅 | 무료 |
| Instagram Graph API | Instagram 배포 | 무료 (비즈니스 계정) |
| X (Twitter) API v2 | X 스레드 배포 | 유료 ($100/월~) |

> **최소 구성**: `ANTHROPIC_API_KEY` + `BRAVE_API_KEY` 만 있어도 콘텐츠 생성까지 가능.  
> Blogger 발행은 Google OAuth2 추가 필요.

---

## 환경변수

`.env.example`을 참고해 `.env` 파일을 작성하세요.

```env
# 필수
ANTHROPIC_API_KEY=sk-ant-...
BRAVE_API_KEY=BSA...

# Blogger 발행 (선택)
BLOGGER_BLOG_ID=123456789
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# SNS 배포 (선택)
INSTAGRAM_ACCESS_TOKEN=...
X_API_KEY=...
```

전체 목록은 [`.env.example`](.env.example) 참고.

---

## 파이프라인 상세

### Step 1 — Research Agent
- Brave Search로 AI 최신 뉴스 수집
- arXiv API로 관련 논문 검색
- GitHub Trending에서 AI 오픈소스 트렌드 파악
- 당일 핫토픽 3개 자동 선정 (검색량 + 뉴스성 + 경쟁도 스코어링)

### Step 2 — SEO Agent
- Claude API로 주제별 SEO 구조 설계
- 메인 키워드 + LSI 키워드 5개 선정
- 검색 의도 분류 (정보습득 / 비교 / 방법 / 최신동향)
- Title / Meta Description / URL Slug / H1~H3 / ToC / FAQ 자동 생성
- Featured Snippet 타겟 문구 생성

### Step 3 — Writer Agent
- SEO 구조 기반으로 3,000자+ 포스트 작성
- 핵심 요약 박스 / ToC / FAQ Schema / JSON-LD 포함
- E-E-A-T 원칙 적용 (전문성 + 출처 명시)
- 자동 SEO 검증 후 미통과 시 재시도 (최대 2회)

### Step 3.5 — Image Gen Agent
- 썸네일 이미지 (1200×630) 자동 생성
- SNS 카드 이미지 (1080×1080) 자동 생성
- 한글 폰트(NotoSansKR) 적용

### Step 3.9 — SNS Pipeline
- X 스레드 5개 자동 변환
- Instagram 카드 배포
- 주간 뉴스레터 HTML 생성

### Step 4 — Publisher Agent
- Google Blogger API v3로 자동 발행
- 라벨(태그) 자동 설정
- 발행 URL + 결과 로그 저장

---

## 출력 예시

```
[2026-03-27 03:06 UTC] P004 Daily Pipeline 시작 — 2026-03-27
[Step 1] Research — 3개 주제 선정 완료
[Step 2] SEO — 3개 SEO 계획 생성 완료
  [1] Claude AI 최신 기능 2025 총정리 | FAQ: 7개 | 섹션: 7개 ✅
  [2] AI 에이전트 자동화 워크플로우 완벽 가이드 2025 ✅
  [3] Gemini 2.0 Flash 성능 분석: GPT-4o보다 2배 빠른 이유 ✅
[Step 3] Writer — 3/3 포스트 3,000자 이상
[Step 3.5] Image Gen — 3개 썸네일 + 카드 생성
[Step 3.7] SEO 검증 — 3/3 통과
[Step 3.9] SNS — 스레드 3개 + 뉴스레터 생성
[Step 4] Publisher — 3/3 발행 성공
파이프라인 완료 — 총 소요: 1072s
```

---

## 크론 설정 (자동 실행)

```bash
# 매일 06:00 KST 자동 실행
0 21 * * * cd /path/to/ai-blog-autopilot && python run_daily.py >> output/logs/cron.log 2>&1
```

---

## 라이선스

MIT License

---

## 기여

PR 환영합니다. 이슈는 GitHub Issues에 남겨주세요.
