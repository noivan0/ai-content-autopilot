# P004 — Google Blogger 포스팅 자동화

## 개요
AI 전문 블로그 자동 운영 시스템. 매일 3개 포스팅, 구글 SEO 최적화, E-E-A-T 기반 고품질 콘텐츠.

## 목표
- 구글 검색 상위 노출
- 클릭률(CTR) 및 조회수 극대화
- 완전 자동화 (Research → 작성 → 포스팅 → 리포트)

---

## 에이전트 구조

### 1. Research Agent (리서치팀)
**역할**: 최신 AI 정보 수집 및 주제 발굴
- 구글 검색, 뉴스, arXiv 논문, GitHub 트렌드, Reddit/HackerNews
- 당일 핫토픽 3개 선정 (검색량 + 뉴스성 + 경쟁도 분석)
- 각 주제별 핵심 자료 수집 및 정리

**출력**: `daily_topics_YYYY-MM-DD.json` (주제 3개 + 참고자료)

### 2. SEO Agent (SEO팀)
**역할**: 키워드 분석 및 SEO 구조 설계
- 주제별 타겟 키워드 1개 + LSI 키워드 5~10개 선정
- 검색 의도(Search Intent) 분석
- 제목(Title), 메타 디스크립션, URL 슬러그 생성
- H1/H2/H3 헤딩 구조 설계

**출력**: `seo_plan_YYYY-MM-DD.json` (포스팅별 SEO 설계)

### 3. Writer Agent (콘텐츠팀)
**역할**: 실제 블로그 포스트 작성
- 3,000자 이상 (공백 제외)
- 유명 AI 블로거 포맷 참고 (서두 → 본론 → 실용 팁 → 결론)
- E-E-A-T 원칙 적용 (전문성, 사실 근거, 출처 명시)
- 검색 의도에 최적화된 답변을 서두에 배치
- 이미지 alt 텍스트, 내부/외부 링크 포함

**출력**: `post_YYYY-MM-DD_N.html` (Blogger 업로드용 HTML)

### 4. Publisher Agent (배포팀)
**역할**: Google Blogger API로 자동 포스팅
- Blogger API v3 인증 및 포스팅
- 라벨(태그) 자동 설정
- 예약 포스팅 (최적 시간 설정)
- 포스팅 결과 확인 및 URL 수집

**출력**: `publish_log_YYYY-MM-DD.json` (포스팅 URL + 상태)

### 5. Analytics Agent (분석팀)
**역할**: 성과 추적 및 피드백
- Google Search Console API 연동
- 포스팅별 클릭수, 노출수, CTR, 평균 순위 수집
- 주간 성과 리포트 생성
- 고성과 포맷 패턴 분석 → Writer Agent에 피드백

**출력**: `weekly_report_YYYY-WW.md`

---

## 워크플로우

```
[매일 06:00 KST]
Research Agent → SEO Agent → Writer Agent → Publisher Agent
                                                    ↓
[매주 월요일]                              Analytics Agent
```

## 디렉토리 구조
```
p004-blog-automation/
├── PROJECT.md
├── .env                    # API 키 (Blogger, Google OAuth)
├── agents/
│   ├── research.py         # 리서치 에이전트
│   ├── seo.py              # SEO 에이전트
│   ├── writer.py           # 작성 에이전트
│   ├── publisher.py        # 배포 에이전트
│   └── analytics.py        # 분석 에이전트
├── templates/
│   ├── post_template.html  # 포스트 HTML 템플릿
│   └── seo_checklist.md    # SEO 체크리스트
├── output/
│   ├── topics/             # 주제 파일
│   ├── seo/                # SEO 계획
│   ├── posts/              # 작성된 포스트
│   └── logs/               # 배포/분석 로그
└── run_daily.py            # 메인 실행 스크립트
```

## 필요 API
- Google Blogger API v3 (포스팅)
- Google Search Console API (성과 분석)
- Google OAuth 2.0 (인증)
- Anthropic Claude API (콘텐츠 생성)
- Brave Search API (리서치)

## 파라미터
- 포스팅 수: 3개/일
- 최소 글자수: 3,000자 (공백 제외)
- 포스팅 시간: 07:00 / 12:00 / 18:00 KST
- 주제: AI, LLM, Claude, OpenClaw, 인공지능 최신 동향
- 언어: 한국어 (추후 영어 확장 가능)
