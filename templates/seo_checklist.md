# SEO 발행 전 체크리스트 — P004 Blog Automation
**기준: Google SEO 2025 최적화**
**업데이트: 2025-03**

---

## ✅ 필수 항목 (13개) — 모두 통과해야 발행

| # | 항목 | 기준 | 확인 |
|---|------|------|------|
| 1 | **제목 길이 및 키워드 배치** | 60자 이내, 메인 키워드 앞쪽에 배치 | ☐ |
| 2 | **메타 설명 길이** | 120~155자 (검색 결과 잘림 방지) | ☐ |
| 3 | **H1 키워드 포함** | `<h1>` 태그에 메인 키워드 반드시 포함 | ☐ |
| 4 | **핵심 요약 박스** | `<div class="summary-box">` — H1 바로 다음, 3줄 이내 즉시 답변 | ☐ |
| 5 | **목차(ToC) 존재** | `<nav class="toc">` — 4개 이상 H2 섹션이면 필수 | ☐ |
| 6 | **FAQ 5개 이상** | `<section class="faq">` — People Also Ask 타겟 Q&A 최소 5개 | ☐ |
| 7 | **Article Schema JSON-LD** | `<script type="application/ld+json">` — Article 타입 | ☐ |
| 8 | **FAQPage Schema JSON-LD** | `<script type="application/ld+json">` — FAQPage 타입 (별도) | ☐ |
| 9 | **외부 권위 링크 2개 이상** | `target="_blank" rel="noopener noreferrer"` 필수 | ☐ |
| 10 | **내부 링크 2개 이상** | 관련 포스트로 연결 (사이트 체류시간↑) | ☐ |
| 11 | **글자수 3,000자 이상** | 공백 제외 순수 본문 기준 (FAQ, JSON-LD 제외) | ☐ |
| 12 | **이미지 alt 텍스트** | 모든 `<img>`에 키워드 포함 alt 텍스트 | ☐ |
| 13 | **URL slug 형식** | 영문 소문자 + 하이픈 (`my-post-slug`), 한글/특수문자 금지 | ☐ |

---

## 🔶 권장 항목 (5개) — 가능하면 적용

| # | 항목 | 기준 | 확인 |
|---|------|------|------|
| 1 | **LSI 키워드 분산 배치** | 보조 키워드 5개를 H2 헤딩과 본문에 자연스럽게 배치 (밀도 1~2%) | ☐ |
| 2 | **첫 문단 메인 키워드** | 도입부 첫 번째 `<p>` 내에 메인 키워드 등장 | ☐ |
| 3 | **구조화 콘텐츠 1개 이상** | 표(`<table>`), 불릿(`<ul>`), 코드블록(`<code>`) 중 1개 이상 | ☐ |
| 4 | **읽기 시간 명시** | 도입부에 예상 읽기 시간 표시 (예: "약 12분 소요") | ☐ |
| 5 | **결론 CTA 존재** | 관련 포스트 유도, 뉴스레터 구독 등 독자 행동 유도 문구 | ☐ |

---

## 🔍 자동 검증 (validate_post_seo)

`run_daily.py`가 Writer 완료 후 자동으로 아래 항목을 검증합니다:

```python
# run_daily.py Step 3.5 — SEO 자동 검증
issues = validate_post_seo(html, meta)
```

| 검증 항목 | 조건 |
|----------|------|
| H1 존재 | `<h1` 포함 |
| 핵심 요약 박스 | `summary-box` 클래스 포함 |
| 목차 | `class="toc"` 포함 |
| FAQ 섹션 | `class="faq"` 포함 |
| Schema JSON-LD | `application/ld+json` 포함 |
| 외부 링크 수 | `target="_blank"` 2개 이상 |
| 글자수 | `char_count` >= 3,000 |

검증 결과: `output/logs/seo_validation_YYYY-MM-DD.json`

---

## 📋 발행 전 최종 확인 순서

```
1. [ ] writer.py가 생성한 HTML 파일 열기
2. [ ] 필수 항목 13개 체크
3. [ ] validate_post_seo 결과 확인 (issues 리스트 비어있어야 함)
4. [ ] 이미지 placeholder.jpg → 실제 이미지 URL 교체
5. [ ] 내부 링크 href → 실제 발행된 포스트 URL 교체
6. [ ] 외부 링크 유효성 확인 (404 없어야 함)
7. [ ] JSON-LD FAQ 내용이 HTML FAQ 섹션과 일치하는지 확인
8. [ ] Blogger 미리보기로 모바일 렌더링 확인
9. [ ] 예약 시간 (KST) 확인
10.[ ] 발행!
```

---

## 💡 자주 하는 실수

| 실수 | 올바른 방법 |
|------|-----------|
| H1을 여러 개 사용 | 페이지당 H1은 반드시 1개만 |
| FAQ JSON-LD와 HTML 내용 불일치 | 두 곳 내용 동기화 필수 |
| 외부 링크에 rel="noopener" 누락 | 보안 + SEO 모두 불이익 |
| URL slug에 한글 사용 | 영문+하이픈으로만 구성 |
| 이미지 alt에 키워드 없음 | 이미지 검색 유입 손실 |
| 메타 설명 160자 초과 | 검색 결과에서 잘려서 표시됨 |
| ToC 앵커와 H2 id 불일치 | 클릭해도 이동 안 됨 |

---

*이 체크리스트는 `agents/seo.py`의 `check_seo_quality()` 및 `run_daily.py`의 `validate_post_seo()`와 연동됩니다.*
