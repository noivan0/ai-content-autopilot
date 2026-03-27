#!/usr/bin/env python3
"""
P004 콘텐츠 품질 검증 테스트 스크립트
임의 키워드로 전체 파이프라인 실행 후 품질 리포트 생성

사용법:
  python3 test_content_quality.py                        # 기본 키워드 3개
  python3 test_content_quality.py "Claude AI 최신 기능"  # 키워드 지정
  python3 test_content_quality.py --no-api               # Claude API 없이 Mock 모드
"""
import os, sys, json, re, datetime, time, textwrap, urllib.request, urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

TODAY = datetime.date.today().isoformat()
NO_API = "--no-api" in sys.argv

# ── 색상 출력 ──────────────────────────────────────────────────────────────────
class C:
    PASS  = "\033[92m✅"
    FAIL  = "\033[91m❌"
    WARN  = "\033[93m⚠️ "
    INFO  = "\033[94mℹ️ "
    BOLD  = "\033[1m"
    RESET = "\033[0m"

def p(icon, msg): print(f"  {icon} {msg}{C.RESET}")
def section(title): print(f"\n{C.BOLD}{'─'*60}\n  {title}\n{'─'*60}{C.RESET}")

# ── Mock 포스트 생성 (Claude API 없을 때) ────────────────────────────────────
MOCK_HTML_TEMPLATE = """<article itemscope itemtype="https://schema.org/Article">
<h1 itemprop="headline">{title}</h1>

<div class="summary-box" style="background:#f0f7ff;border-left:4px solid #1a73e8;padding:16px 20px;margin:20px 0;border-radius:4px;">
  <strong>💡 핵심 요약</strong>
  <p>{keyword}에 대한 핵심 내용을 3줄로 요약합니다. 이 글에서 최신 동향, 실전 활용법, 향후 전망을 다룹니다.</p>
</div>

<nav class="toc" style="background:#f9f9f9;border:1px solid #e0e0e0;padding:16px 20px;margin:20px 0;border-radius:4px;">
  <strong>📋 목차</strong>
  <ol>
    <li><a href="#section-1">{keyword}란 무엇인가?</a></li>
    <li><a href="#section-2">핵심 기능과 특징</a></li>
    <li><a href="#section-3">실전 활용 가이드</a></li>
    <li><a href="#section-4">성능 비교 분석</a></li>
    <li><a href="#section-5">향후 전망</a></li>
  </ol>
</nav>

<h2 id="section-1">{keyword}란 무엇인가?</h2>
<p>{keyword}는 현재 AI 분야에서 가장 주목받는 기술 중 하나입니다. 2024년부터 본격적으로 주목받기 시작했으며,
특히 자연어 처리와 멀티모달 처리 능력에서 탁월한 성능을 보여주고 있습니다. 전문가들은 이 기술이
향후 5년 내에 산업 전반에 걸쳐 혁신을 가져올 것으로 예측하고 있습니다.</p>
<p>기존 기술과의 가장 큰 차이점은 컨텍스트 이해 능력입니다. 단순한 패턴 매칭을 넘어서,
실제로 문맥을 이해하고 추론하는 능력을 갖추고 있습니다. 이는 실무 적용 가능성을 크게 높였습니다.
<a href="https://arxiv.org/abs/2303.08774" target="_blank" rel="noopener noreferrer">관련 논문 보기</a></p>

<h2 id="section-2">핵심 기능과 특징</h2>
<p>{keyword}의 주요 기능은 크게 세 가지로 나눌 수 있습니다. 첫째, 고도의 언어 이해 능력입니다.
단순한 키워드 매칭이 아닌 의미론적 이해를 바탕으로 정확한 답변을 제공합니다.
둘째, 멀티모달 처리 능력으로 텍스트, 이미지, 코드를 동시에 처리할 수 있습니다.</p>
<ul>
  <li><strong>언어 이해</strong>: 복잡한 맥락을 정확히 파악</li>
  <li><strong>코드 생성</strong>: 다양한 프로그래밍 언어 지원</li>
  <li><strong>분석 능력</strong>: 데이터 분석 및 인사이트 도출</li>
  <li><strong>창작 능력</strong>: 고품질 콘텐츠 생성</li>
</ul>
<p>특히 한국어 처리 능력이 대폭 향상되어, 국내 기업들의 도입도 빠르게 증가하고 있습니다.
<a href="https://www.example.com/report" target="_blank" rel="noopener noreferrer">시장 조사 보고서</a>에 따르면
국내 AI 도입 기업의 78%가 생산성 향상을 경험했다고 합니다.</p>

<h2 id="section-3">실전 활용 가이드</h2>
<p>{keyword}를 실무에서 효과적으로 활용하는 방법을 단계별로 알아보겠습니다.
무엇보다 중요한 것은 구체적인 프롬프트 설계입니다. 모호한 질문보다는 명확한 목표와
컨텍스트를 제공할수록 더 좋은 결과를 얻을 수 있습니다.</p>
<p>실제 사용 사례를 보면, 마케팅 팀에서는 콘텐츠 초안 작성 시간을 70% 단축했고,
개발팀에서는 코드 리뷰 속도가 3배 향상되었습니다. 고객 서비스 분야에서도 응답 품질이
크게 개선되었습니다. <a href="https://www.naver.com" target="_blank" rel="noopener noreferrer">더 많은 사례 보기</a></p>
<!-- IMAGE: {keyword} 활용 사례 인포그래픽 -->
<figure>
  <img alt="{keyword} 활용 사례 다이어그램" src="placeholder.jpg" loading="lazy">
  <figcaption>{keyword} 실전 활용 흐름도</figcaption>
</figure>

<h2 id="section-4">성능 비교 분석</h2>
<p>주요 경쟁 솔루션과의 비교 분석 결과, {keyword}는 특히 한국어 처리와 복잡한 추론 태스크에서
두드러진 우위를 보였습니다. 벤치마크 테스트에서 평균 92점을 기록, 2위와 8점 차이를 보였습니다.</p>
<table style="width:100%;border-collapse:collapse;margin:16px 0;">
  <tr style="background:#f0f7ff"><th style="padding:8px;border:1px solid #ddd">항목</th><th style="padding:8px;border:1px solid #ddd">{keyword}</th><th style="padding:8px;border:1px solid #ddd">경쟁사 A</th><th style="padding:8px;border:1px solid #ddd">경쟁사 B</th></tr>
  <tr><td style="padding:8px;border:1px solid #ddd">한국어 처리</td><td style="padding:8px;border:1px solid #ddd">★★★★★</td><td style="padding:8px;border:1px solid #ddd">★★★★☆</td><td style="padding:8px;border:1px solid #ddd">★★★☆☆</td></tr>
  <tr><td style="padding:8px;border:1px solid #ddd">응답 속도</td><td style="padding:8px;border:1px solid #ddd">★★★★☆</td><td style="padding:8px;border:1px solid #ddd">★★★★★</td><td style="padding:8px;border:1px solid #ddd">★★★★☆</td></tr>
  <tr><td style="padding:8px;border:1px solid #ddd">비용 효율</td><td style="padding:8px;border:1px solid #ddd">★★★★☆</td><td style="padding:8px;border:1px solid #ddd">★★★☆☆</td><td style="padding:8px;border:1px solid #ddd">★★★★★</td></tr>
</table>

<h2 id="section-5">향후 전망</h2>
<p>{keyword} 기술은 앞으로도 빠르게 발전할 것으로 전망됩니다. 특히 에이전트 기반 자동화와
결합되면서 더욱 강력한 도구로 진화하고 있습니다. 2025년에는 멀티모달 기능이 더욱 강화되고,
실시간 정보 처리 능력도 향상될 것으로 예상됩니다.</p>
<p>기업들의 도입도 가속화될 전망입니다. 현재 도입을 검토 중인 기업은 전년 대비 340% 증가했으며,
특히 중소기업의 관심이 크게 늘었습니다. 비용 장벽이 낮아지고 사용 편의성이 높아지면서
더 많은 기업들이 혜택을 누릴 수 있게 되었습니다.</p>
<p>관련 분야도 주목: <a href="/{keyword}-guide">{keyword} 입문 가이드</a> |
<a href="/ai-tools-comparison">AI 도구 비교</a></p>

<section class="faq" itemscope itemtype="https://schema.org/FAQPage">
  <h2>자주 묻는 질문</h2>
  <div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
    <h3 itemprop="name">{keyword}는 무료로 사용할 수 있나요?</h3>
    <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
      <p itemprop="text">기본 기능은 무료로 제공되며, 고급 기능은 유료 플랜을 통해 이용할 수 있습니다.</p>
    </div>
  </div>
  <div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
    <h3 itemprop="name">{keyword}와 기존 AI의 차이점은 무엇인가요?</h3>
    <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
      <p itemprop="text">더 높은 수준의 언어 이해와 추론 능력을 갖추고 있으며, 한국어 처리에서 특히 우수한 성능을 보입니다.</p>
    </div>
  </div>
  <div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
    <h3 itemprop="name">비즈니스에 어떻게 활용할 수 있나요?</h3>
    <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
      <p itemprop="text">콘텐츠 작성, 고객 서비스, 데이터 분석, 코드 생성 등 다양한 분야에서 생산성 향상에 활용할 수 있습니다.</p>
    </div>
  </div>
  <div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
    <h3 itemprop="name">데이터 보안은 어떻게 보장되나요?</h3>
    <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
      <p itemprop="text">엔터프라이즈 플랜에서는 데이터 격리와 암호화를 통해 보안이 보장됩니다.</p>
    </div>
  </div>
  <div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
    <h3 itemprop="name">초보자도 쉽게 사용할 수 있나요?</h3>
    <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
      <p itemprop="text">직관적인 인터페이스와 다양한 가이드를 제공하여 기술 배경 없이도 쉽게 시작할 수 있습니다.</p>
    </div>
  </div>
</section>

<div style="background:#f9f9f9;border-left:4px solid #1a73e8;padding:16px;margin:24px 0;">
  <strong>✅ 결론</strong>
  <p>{keyword}는 현재 AI 시장에서 가장 주목받는 기술 중 하나입니다.
  특히 한국어 처리와 복잡한 추론 능력에서 탁월한 성능을 보여줍니다.
  도입을 검토하고 있다면, 지금이 최적의 시기입니다.</p>
  <p>더 알아보기: <a href="/ai-guide">AI 활용 완벽 가이드 →</a></p>
</div>

<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{title}",
  "description": "{keyword}에 대한 완벽 가이드",
  "author": {{"@type": "Organization", "name": "AI 인사이트"}},
  "datePublished": "{today}"
}}
</script>
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {{"@type": "Question", "name": "{keyword}는 무료인가요?", "acceptedAnswer": {{"@type": "Answer", "text": "기본 기능은 무료입니다."}}}}
  ]
}}
</script>
</article>"""

# ── SEO 검증 ──────────────────────────────────────────────────────────────────
def validate_seo(html: str, keyword: str) -> dict:
    checks = {}
    issues = []

    # 1. H1 존재
    checks["H1 태그"] = "<h1" in html.lower()
    if not checks["H1 태그"]: issues.append("H1 없음")

    # 2. 핵심 요약 박스
    checks["핵심 요약 박스"] = "summary-box" in html
    if not checks["핵심 요약 박스"]: issues.append("핵심 요약 박스 없음")

    # 3. ToC
    checks["목차(ToC)"] = 'class="toc"' in html or "class='toc'" in html
    if not checks["목차(ToC)"]: issues.append("ToC 없음")

    # 4. FAQ 섹션
    checks["FAQ 섹션"] = 'class="faq"' in html or "class='faq'" in html
    if not checks["FAQ 섹션"]: issues.append("FAQ 없음")

    # 5. Schema JSON-LD (Article + FAQPage)
    ld_count = html.count("application/ld+json")
    checks["Schema JSON-LD (2개)"] = ld_count >= 2
    if ld_count < 2: issues.append(f"JSON-LD {ld_count}개 (2개 필요)")

    # 6. 외부 링크
    ext_links = html.count('target="_blank"')
    checks[f"외부 링크 (≥2개, 현재 {ext_links}개)"] = ext_links >= 2
    if ext_links < 2: issues.append(f"외부 링크 {ext_links}개 (2개 필요)")

    # 7. 내부 링크
    int_links = len(re.findall(r'href=["\']/', html))
    checks[f"내부 링크 (≥2개, 현재 {int_links}개)"] = int_links >= 2
    if int_links < 2: issues.append(f"내부 링크 {int_links}개 (2개 권장)")

    # 8. 이미지 alt 텍스트
    empty_alts = len(re.findall(r'<img[^>]*alt\s*=\s*["\']["\']', html))
    checks["이미지 alt 텍스트"] = empty_alts == 0
    if empty_alts > 0: issues.append(f"빈 alt 텍스트 {empty_alts}개")

    # 9. 글자수 (FAQ, JSON-LD 제외 순수 본문)
    clean = re.sub(r'<section[^>]*class=["\']faq["\'][^>]*>.*?</section>', '', html, flags=re.DOTALL|re.I)
    clean = re.sub(r'<script[^>]*>.*?</script>', '', clean, flags=re.DOTALL)
    clean = re.sub(r'<[^>]+>', '', clean)
    clean = re.sub(r'\s+', '', clean)
    char_count = len(clean)
    checks[f"글자수 (≥3,000자, 현재 {char_count:,}자)"] = char_count >= 3000
    if char_count < 3000: issues.append(f"글자수 부족 ({char_count:,}자 < 3,000자)")

    # 10. 키워드 포함
    kw_count = html.lower().count(keyword.lower())
    checks[f"키워드 밀도 (현재 {kw_count}회)"] = kw_count >= 3
    if kw_count < 3: issues.append(f"키워드 밀도 낮음 ({kw_count}회)")

    # 11. H2 구조 (4개 이상)
    h2_count = len(re.findall(r'<h2', html, re.I))
    checks[f"H2 구조 (≥4개, 현재 {h2_count}개)"] = h2_count >= 4
    if h2_count < 4: issues.append(f"H2 섹션 {h2_count}개 (4개 권장)")

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    score = int(passed / total * 100)

    return {
        "checks": checks,
        "issues": issues,
        "passed": passed,
        "total": total,
        "score": score,
        "char_count": char_count,
    }


# ── 콘텐츠 품질 지표 ──────────────────────────────────────────────────────────
def analyze_content_quality(html: str, keyword: str) -> dict:
    """가독성, 구조, 정보 밀도 분석"""
    text = re.sub(r'<[^>]+>', '', html)
    text = re.sub(r'\s+', ' ', text).strip()
    words = text.split()
    sentences = re.split(r'[.!?。]', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

    avg_sentence_len = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)

    # 정보 요소 카운트
    has_table = '<table' in html.lower()
    has_list = '<ul' in html.lower() or '<ol' in html.lower()
    has_code = '<code' in html.lower() or '<pre' in html.lower()
    has_img = '<img' in html.lower()
    h2_count = len(re.findall(r'<h2', html, re.I))
    h3_count = len(re.findall(r'<h3', html, re.I))

    return {
        "총 단어수": len(words),
        "문장 수": len(sentences),
        "평균 문장 길이": f"{avg_sentence_len:.1f}단어",
        "H2 섹션": h2_count,
        "H3 소제목": h3_count,
        "표 포함": "✅" if has_table else "❌",
        "목록 포함": "✅" if has_list else "❌",
        "코드 블록": "✅" if has_code else "❌",
        "이미지 포함": "✅" if has_img else "❌",
    }


# ── SNS 콘텐츠 검증 ────────────────────────────────────────────────────────────
def validate_sns_content(thread_path: str, card_path: str, newsletter_path: str) -> dict:
    results = {}

    # X 스레드 검증
    if thread_path and os.path.exists(thread_path):
        with open(thread_path) as f:
            threads = json.load(f)
        tweet_count = len(threads)
        all_under_280 = all(t["char_count"] <= 280 for t in threads)
        results["X 스레드"] = {
            "트윗 수": tweet_count,
            "280자 이하": "✅" if all_under_280 else "❌",
            "CTA 포함": "✅" if any("http" in t["text"] or "링크" in t["text"] for t in threads) else "❌",
            "해시태그 포함": "✅" if any("#" in t["text"] for t in threads) else "❌",
            "tweets": [{"order": t["order"], "chars": t["char_count"], "preview": t["text"][:60]+"..."} for t in threads],
        }
    else:
        results["X 스레드"] = {"상태": "❌ 파일 없음"}

    # 카드 이미지 검증
    if card_path and os.path.exists(card_path):
        size = os.path.getsize(card_path)
        results["인스타 카드"] = {
            "파일 존재": "✅",
            "파일 크기": f"{size//1024}KB",
            "크기 적정 (>10KB)": "✅" if size > 10240 else "❌",
        }
    else:
        results["인스타 카드"] = {"상태": "❌ 파일 없음"}

    # 뉴스레터 검증
    if newsletter_path and os.path.exists(newsletter_path):
        with open(newsletter_path, encoding='utf-8') as f:
            nl = f.read()
        results["뉴스레터"] = {
            "파일 존재": "✅",
            "HTML 구조": "✅" if "<!DOCTYPE html>" in nl else "❌",
            "블로그 링크 포함": "✅" if "href=" in nl else "❌",
            "핵심 포인트 포함": "✅" if "<li>" in nl else "❌",
        }
    else:
        results["뉴스레터"] = {"상태": "❌ 파일 없음"}

    return results


# ── 테스트 키워드 설정 ────────────────────────────────────────────────────────
TEST_KEYWORDS = [
    {
        "keyword": "Claude AI 최신 기능",
        "title": "Claude AI 최신 기능 완벽 가이드: 2025년 업데이트 총정리",
        "slug": "claude-ai-latest-features",
        "domain": "Claude Anthropic",
        "labels": ["Claude", "Anthropic", "AI", "LLM"],
        "meta_description": "Claude AI의 2025년 최신 기능을 완벽하게 분석합니다. 코드 작성, 문서 분석, 멀티모달 기능까지.",
        "key_points": ["Claude 3.7은 수학·코딩에서 최고 성능", "200K 컨텍스트로 초대용량 문서 처리", "한국어 처리 능력이 대폭 향상됨"],
    },
    {
        "keyword": "AI 에이전트 자동화",
        "title": "AI 에이전트 자동화: 업무 효율 300% 높이는 실전 가이드",
        "slug": "ai-agent-automation-guide",
        "domain": "AI 에이전트 자동화",
        "labels": ["AI에이전트", "자동화", "LLM", "생산성"],
        "meta_description": "AI 에이전트로 반복 업무를 자동화하는 방법. 도구 선택부터 구현까지 단계별 가이드.",
        "key_points": ["AI 에이전트로 반복 업무 90% 자동화 가능", "OpenAI + LangChain 조합이 가장 실용적", "월 100만원 이하 비용으로 구축 가능"],
    },
    {
        "keyword": "Gemini 2.0 Flash",
        "title": "Gemini 2.0 Flash 완전 분석: Google AI의 속도 혁신",
        "slug": "gemini-2-flash-analysis",
        "domain": "Gemini Google AI",
        "labels": ["Gemini", "Google", "AI", "LLM"],
        "meta_description": "Gemini 2.0 Flash의 성능, 속도, 비용을 GPT-4o와 비교 분석합니다.",
        "key_points": ["GPT-4o 대비 응답 속도 2배 빠름", "멀티모달 기능으로 이미지·음성 동시 처리", "API 비용이 경쟁사 대비 40% 저렴"],
    },
]

# ── 메인 실행 ──────────────────────────────────────────────────────────────────
def main():
    print(f"\n{C.BOLD}{'='*60}")
    print(f"  P004 콘텐츠 품질 검증 테스트")
    print(f"  {'[Mock 모드 - Claude API 없음]' if NO_API else '[API 모드]'}")
    print(f"  날짜: {TODAY}")
    print(f"{'='*60}{C.RESET}")

    # 커맨드라인 키워드 지정
    custom_kw = [a for a in sys.argv[1:] if not a.startswith("--")]
    if custom_kw:
        kw = custom_kw[0]
        test_cases = [{
            "keyword": kw,
            "title": f"{kw} 완벽 가이드: 최신 동향과 실전 활용법",
            "slug": kw.lower().replace(" ", "-"),
            "domain": "LLM 언어모델",
            "labels": [kw, "AI", "인공지능"],
            "meta_description": f"{kw}에 대한 완벽 가이드입니다.",
            "key_points": [f"{kw} 핵심 기능 분석", "실전 적용 사례", "향후 전망"],
        }]
    else:
        test_cases = TEST_KEYWORDS

    all_scores = []
    os.makedirs(os.path.join(BASE, "output", "posts"), exist_ok=True)
    os.makedirs(os.path.join(BASE, "output", "images"), exist_ok=True)
    os.makedirs(os.path.join(BASE, "output", "threads"), exist_ok=True)
    os.makedirs(os.path.join(BASE, "output", "newsletters"), exist_ok=True)

    for i, tc in enumerate(test_cases, 1):
        kw    = tc["keyword"]
        title = tc["title"]
        slug  = tc["slug"]

        section(f"[{i}/{len(test_cases)}] 키워드: {kw}")

        # ── 1. HTML 생성 ───────────────────────────────────────────────────
        print(f"\n  {C.BOLD}STEP 1 — 콘텐츠 생성{C.RESET}")
        if NO_API:
            html = MOCK_HTML_TEMPLATE.format(
                title=title, keyword=kw, today=TODAY
            )
            p(C.INFO, f"Mock HTML 생성 (Claude API 없음)")
        else:
            try:
                import urllib.request as _ur, urllib.error as _ue
                _api_key  = os.environ.get("ANTHROPIC_API_KEY", "")
                _base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
                _model    = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
                prompt = f"""다음 키워드로 SEO 최적화된 한국어 블로그 포스트 HTML을 작성하세요.

키워드: {kw}
제목: {title}

반드시 포함해야 할 구조 (순서 엄수):
1. <article itemscope itemtype="https://schema.org/Article"> 래퍼
2. <h1 itemprop="headline">제목</h1>
3. <div class="summary-box"> 핵심 요약 3줄 </div>
4. <nav class="toc"> 목차 (H2 5개 이상 연결) </nav>
5. H2 섹션 5개 이상 (각 300자 이상, id 앵커 포함)
6. 외부 링크 3개 이상 (target="_blank" rel="noopener noreferrer")
7. 내부 링크 3개 이상 (href="/관련글")
8. <section class="faq"> FAQ 5개 (Schema.org 마크업 포함) </section>
9. 결론 + CTA
10. Article JSON-LD + FAQPage JSON-LD (두 개 모두)
11. </article>

공백 제외 순수 본문 3,500자 이상 (FAQ, JSON-LD 제외).
HTML만 출력하세요. 설명 없이."""
                payload = json.dumps({
                    "model": _model, "max_tokens": 8000,
                    "messages": [{"role": "user", "content": prompt}]
                }).encode()
                req = _ur.Request(
                    f"{_base_url}/messages", data=payload,
                    headers={"Content-Type": "application/json",
                             "x-api-key": _api_key,
                             "anthropic-version": "2023-06-01"},
                    method="POST"
                )
                with _ur.urlopen(req, timeout=180) as r:
                    html = json.loads(r.read())["content"][0]["text"].strip()
                if "<article" in html and not html.startswith("<article"):
                    html = html[html.index("<article"):]
                p(C.PASS, f"Claude API({_model})로 HTML 생성 완료")
            except Exception as e:
                p(C.WARN, f"Claude API 실패 ({e}) → Mock으로 전환")
                html = MOCK_HTML_TEMPLATE.format(
                    title=title, keyword=kw, today=TODAY
                )

        html_path = os.path.join(BASE, "output", "posts", f"test_{TODAY}_{slug}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        p(C.PASS, f"HTML 저장: {os.path.relpath(html_path, BASE)}")

        # ── 2. SEO 검증 ───────────────────────────────────────────────────
        print(f"\n  {C.BOLD}STEP 2 — SEO 구조 검증{C.RESET}")
        seo = validate_seo(html, kw)
        for check, passed in seo["checks"].items():
            icon = C.PASS if passed else C.FAIL
            p(icon, check)
        print(f"\n  {C.BOLD}SEO 점수: {seo['score']}점 ({seo['passed']}/{seo['total']} 항목 통과){C.RESET}")
        if seo["issues"]:
            p(C.WARN, "이슈: " + " | ".join(seo["issues"]))

        # ── 3. 콘텐츠 품질 분석 ──────────────────────────────────────────
        print(f"\n  {C.BOLD}STEP 3 — 콘텐츠 품질 분석{C.RESET}")
        quality = analyze_content_quality(html, kw)
        for k, v in quality.items():
            p(C.INFO, f"{k}: {v}")

        # ── 4. 이미지 생성 ────────────────────────────────────────────────
        print(f"\n  {C.BOLD}STEP 4 — 이미지 생성{C.RESET}")
        post_meta = {
            "post_num": i,
            "title": title,
            "slug": slug,
            "primary_keyword": kw,
            "secondary_keywords": tc.get("labels", []),
            "domain": tc.get("domain", ""),
            "labels": tc.get("labels", []),
            "char_count": seo["char_count"],
            "key_points": tc.get("key_points", []),
            "html_file": os.path.basename(html_path),
            "meta_description": tc.get("meta_description", ""),
        }
        thumb_path = card_path = ""
        try:
            from agents.image_gen import run as run_image_gen
            write_data = {"date": TODAY, "posts": [post_meta]}
            img_result = run_image_gen(write_data)
            imgs = img_result.get("images", [])
            if imgs:
                thumb_path = imgs[0].get("thumbnail", "")
                card_path  = imgs[0].get("card", "")
                # image_gen은 상대경로 반환 → 절대경로로 변환
                if thumb_path and not os.path.isabs(thumb_path):
                    thumb_path = os.path.join(BASE, thumb_path)
                if card_path and not os.path.isabs(card_path):
                    card_path = os.path.join(BASE, card_path)
                if thumb_path and os.path.exists(os.path.join(BASE, thumb_path)):
                    p(C.PASS, f"썸네일 생성: {thumb_path}")
                if card_path and os.path.exists(os.path.join(BASE, card_path)):
                    p(C.PASS, f"인스타 카드 생성: {card_path}")
        except Exception as e:
            p(C.FAIL, f"이미지 생성 실패: {e}")

        # ── 5. SNS 변환 ───────────────────────────────────────────────────
        print(f"\n  {C.BOLD}STEP 5 — SNS 콘텐츠 변환{C.RESET}")
        article = {
            "title": title,
            "meta": tc.get("meta_description", ""),
            "slug": slug,
            "tags": tc.get("labels", [])[:5],
            "corner": "AI 소식",
            "key_points": tc.get("key_points", []),
            "domain": tc.get("domain", ""),
        }
        thread_path = nl_path = ""
        try:
            from agents.converters.thread_converter import convert as thread_convert
            threads = thread_convert(article, save_file=True)
            thread_files = [f for f in os.listdir(os.path.join(BASE, "output", "threads"))
                           if slug in f]
            thread_path = os.path.join(BASE, "output", "threads", thread_files[-1]) if thread_files else ""
            p(C.PASS, f"X 스레드 생성: {len(threads)}개 트윗")
            for t in threads:
                print(f"      [{t['order']}] ({t['char_count']}자) {t['text'][:70]}...")
        except Exception as e:
            p(C.FAIL, f"X 스레드 변환 실패: {e}")

        try:
            from agents.converters.newsletter_converter import generate_weekly
            nl_html = generate_weekly([article], save_file=True)
            nl_files = sorted([f for f in os.listdir(os.path.join(BASE, "output", "newsletters"))
                              if f.startswith("weekly_")])
            nl_path = os.path.join(BASE, "output", "newsletters", nl_files[-1]) if nl_files else ""
            p(C.PASS, f"뉴스레터 HTML 생성")
        except Exception as e:
            p(C.FAIL, f"뉴스레터 변환 실패: {e}")

        # ── 6. SNS 콘텐츠 검증 ────────────────────────────────────────────
        print(f"\n  {C.BOLD}STEP 6 — SNS 콘텐츠 검증{C.RESET}")
        # card_path는 image_gen에서 절대경로로 반환됨
        abs_card = card_path if card_path else ""
        sns = validate_sns_content(thread_path, abs_card, nl_path)
        for platform, checks in sns.items():
            print(f"\n  [{platform}]")
            for k, v in checks.items():
                if k == "tweets":
                    continue
                p(C.INFO, f"{k}: {v}")

        all_scores.append({"keyword": kw, "seo_score": seo["score"], "issues": seo["issues"]})
        print()

    # ── 최종 리포트 ───────────────────────────────────────────────────────
    section("최종 품질 리포트")
    print(f"\n  {'키워드':<30} {'SEO점수':>8} {'상태':>6}")
    print(f"  {'─'*50}")
    for s in all_scores:
        icon = "✅" if s["seo_score"] >= 80 else ("⚠️ " if s["seo_score"] >= 60 else "❌")
        print(f"  {s['keyword'][:28]:<30} {s['seo_score']:>7}점 {icon}")
        if s["issues"]:
            for issue in s["issues"]:
                print(f"    └ {issue}")

    avg = sum(s["seo_score"] for s in all_scores) / max(len(all_scores), 1)
    print(f"\n  {C.BOLD}평균 SEO 점수: {avg:.1f}점{C.RESET}")

    # 결과 저장
    report = {
        "date": TODAY,
        "mode": "mock" if NO_API else "api",
        "test_count": len(all_scores),
        "avg_seo_score": round(avg, 1),
        "results": all_scores,
    }
    report_path = os.path.join(BASE, "output", "logs", f"quality_report_{TODAY}.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n  리포트 저장: {os.path.relpath(report_path, BASE)}")

    print(f"\n{C.BOLD}{'='*60}")
    print(f"  생성된 파일 목록")
    print(f"{'='*60}{C.RESET}")
    for d in ["output/posts", "output/images", "output/threads", "output/newsletters"]:
        dpath = os.path.join(BASE, d)
        if os.path.exists(dpath):
            files = [f for f in os.listdir(dpath) if TODAY in f or "weekly_" in f]
            if files:
                print(f"\n  📁 {d}/")
                for f in sorted(files):
                    size = os.path.getsize(os.path.join(dpath, f))
                    print(f"     {f} ({size//1024}KB)")

    print(f"\n{C.RESET}")


if __name__ == "__main__":
    main()
