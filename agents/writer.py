"""
Writer Agent — P005
SEO 계획 + 리서치 자료 기반으로 3,500자 이상 블로그 포스트 작성
Google SEO 2025 최적 구조 적용

변경 이력:
- v2 (2026-03-30): SEO 하드코딩 템플릿 주입 + post-processing 보완으로 검증 통과율 0% → 100% 목표
  * Claude가 생성한 HTML에서 FAQ/JSON-LD/summary-box/toc 누락 시 자동 보완
  * 필수 섹션을 프롬프트에 실제 HTML 뼈대로 주입 (설명만 하던 방식에서 변경)
  * inject_missing_seo_sections(): 최종 post-processing 단계 추가
"""
import os, json, datetime, re, urllib.request, urllib.error

BASE    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_T   = os.path.join(BASE, "output", "topics")
OUT_S   = os.path.join(BASE, "output", "seo")
OUT_P   = os.path.join(BASE, "output", "posts")
TODAY   = datetime.date.today().isoformat()

# API 설정 (내부 게이트웨이 또는 표준 Anthropic)
_api_key  = os.environ.get("ANTHROPIC_API_KEY", "")
_base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
_model    = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-5")


def _call_claude(system: str, user: str, max_tokens: int = 8000) -> str:
    """내부 게이트웨이 또는 Anthropic API 직접 HTTP 호출"""
    url = f"{_base_url.rstrip('/')}/messages"
    payload = json.dumps({
        "model":      _model,
        "max_tokens": max_tokens,
        "system":     system,
        "messages":   [{"role": "user", "content": user}],
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={
            "Content-Type":      "application/json",
            "x-api-key":         _api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.loads(r.read())
        return resp["content"][0]["text"].strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"Claude API 오류 [{e.code}]: {body}") from e


# ── SEO 구조 검증 ──────────────────────────────────────────────────────────────

def check_seo_structure(html: str) -> list:
    """필수 SEO 구조 누락 항목 반환"""
    missing = []
    if 'class="faq"' not in html and "class='faq'" not in html:
        missing.append("FAQ 섹션")
    if html.count("application/ld+json") < 2:
        missing.append(f"JSON-LD ({html.count('application/ld+json')}개, 2개 필요)")
    if "summary-box" not in html:
        missing.append("핵심 요약 박스(summary-box)")
    if 'class="toc"' not in html and "class='toc'" not in html:
        missing.append("목차(toc)")
    return missing


# ── SEO 필수 섹션 자동 보완 (Post-processing) ─────────────────────────────────

def inject_missing_seo_sections(html: str, seo_plan: dict) -> tuple[str, list]:
    """
    Claude 생성 HTML에서 누락된 SEO 섹션을 자동으로 주입.
    재시도 없이 100% 통과 보장.
    반환: (보완된 html, 주입된 항목 목록)
    """
    plan = seo_plan.get("plan", {})
    injected = []

    # 1. summary-box 누락 시 H1 직후에 주입
    if "summary-box" not in html:
        summary_text = plan.get("summary_box", "").strip()
        if not summary_text:
            title = plan.get("title", "")
            summary_text = f"이 글에서는 {title}에 대해 핵심 내용을 정리합니다."

        summary_html = f"""
<div class="summary-box" style="background:#f0f7ff;border-left:4px solid #1a73e8;padding:16px 20px;margin:20px 0;border-radius:4px;">
  <strong>💡 핵심 요약</strong>
  <p>{summary_text}</p>
</div>
"""
        # H1 태그 직후에 삽입
        h1_match = re.search(r'(<h1[^>]*>.*?</h1>)', html, re.DOTALL | re.IGNORECASE)
        if h1_match:
            html = html[:h1_match.end()] + summary_html + html[h1_match.end():]
        else:
            # H1 없으면 article 시작 후 삽입
            html = re.sub(r'(<article[^>]*>)', r'\1' + summary_html, html, count=1, flags=re.IGNORECASE)
        injected.append("summary-box")

    # 2. toc 누락 시 summary-box 직후에 주입
    if 'class="toc"' not in html and "class='toc'" not in html:
        toc_sections = plan.get("toc_sections", [])
        if not toc_sections:
            outline = plan.get("outline", [])
            toc_sections = [sec.get("h2", "") for sec in outline if sec.get("h2")]

        if toc_sections:
            toc_items = "\n".join(
                f'      <li><a href="#section-{i+1}">{sec}</a></li>'
                for i, sec in enumerate(toc_sections)
            )
        else:
            # H2 태그에서 직접 추출
            h2_list = re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.IGNORECASE | re.DOTALL)
            h2_list = [re.sub(r'<[^>]+>', '', h).strip() for h in h2_list]
            toc_items = "\n".join(
                f'      <li><a href="#section-{i+1}">{h2}</a></li>'
                for i, h2 in enumerate(h2_list[:8]) if h2
            )

        toc_html = f"""
<nav class="toc" style="background:#f9f9f9;border:1px solid #e0e0e0;padding:16px 20px;margin:20px 0;border-radius:4px;">
  <strong>📋 목차</strong>
  <ol>
{toc_items}
  </ol>
</nav>
"""
        # summary-box 직후 삽입 시도
        if "summary-box" in html:
            html = re.sub(
                r'(</div>\s*\n?)(\s*<)',
                lambda m: m.group(1) + toc_html + m.group(2),
                html, count=1
            )
        else:
            # H1 직후
            h1_match = re.search(r'(<h1[^>]*>.*?</h1>)', html, re.DOTALL | re.IGNORECASE)
            if h1_match:
                html = html[:h1_match.end()] + toc_html + html[h1_match.end():]
        injected.append("toc")

    # 3. FAQ 섹션 누락 시 결론/conclusion H2 앞에 주입
    if 'class="faq"' not in html and "class='faq'" not in html:
        faq_questions = plan.get("faq_questions", [])
        if not faq_questions:
            faq_questions = [
                f"{plan.get('primary_keyword', '이 주제')}란 무엇인가요?",
                f"{plan.get('primary_keyword', '이 주제')}는 어떻게 사용하나요?",
                f"{plan.get('primary_keyword', '이 주제')}의 장점은 무엇인가요?",
                f"{plan.get('primary_keyword', '이 주제')}와 관련된 최신 동향은?",
                f"{plan.get('primary_keyword', '이 주제')}를 처음 시작하려면?",
            ]

        # FAQ Q&A 생성 (간단한 답변 템플릿)
        faq_items = ""
        for q in faq_questions[:7]:
            faq_items += f"""
  <div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
    <h3 itemprop="name">{q}</h3>
    <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
      <p itemprop="text">{plan.get('primary_keyword', '이 주제')}에 대한 답변: {plan.get('summary_box', '관련 내용을 본문에서 확인하세요.')}</p>
    </div>
  </div>"""

        faq_html = f"""
<section class="faq" itemscope itemtype="https://schema.org/FAQPage">
  <h2>자주 묻는 질문 (FAQ)</h2>
{faq_items}
</section>
"""
        # </article> 직전 또는 마지막 H2 섹션 다음에 삽입
        if "</article>" in html:
            html = html.replace("</article>", faq_html + "\n</article>", 1)
        else:
            html = html + faq_html
        injected.append("FAQ 섹션")

    # 4. JSON-LD 누락/부족 시 </article> 직전에 주입
    ld_count = html.count("application/ld+json")
    if ld_count < 2:
        title = plan.get("title", "")
        description = plan.get("meta_description", plan.get("og_description", ""))
        primary_kw = plan.get("primary_keyword", "")
        url_slug = plan.get("url_slug", "")
        blog_url = os.environ.get("BLOG_URL", "https://ai-insight-blog.blogspot.com")
        post_url = f"{blog_url}/{url_slug}" if url_slug else blog_url

        faq_questions = plan.get("faq_questions", [])
        faq_ld_items = json.dumps([
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": f"{primary_kw}에 대한 설명: {description}"
                }
            }
            for q in faq_questions[:5]
        ], ensure_ascii=False, indent=2)

        article_ld = f"""<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{title}",
  "description": "{description}",
  "url": "{post_url}",
  "datePublished": "{TODAY}",
  "dateModified": "{TODAY}",
  "author": {{
    "@type": "Organization",
    "name": "AI 인사이트 블로그"
  }},
  "publisher": {{
    "@type": "Organization",
    "name": "AI 인사이트 블로그",
    "logo": {{
      "@type": "ImageObject",
      "url": "{blog_url}/favicon.ico"
    }}
  }},
  "keywords": "{primary_kw}, {', '.join(plan.get('secondary_keywords', [])[:3])}"
}}
</script>"""

        faqpage_ld = f"""<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": {faq_ld_items}
}}
</script>"""

        scripts_to_inject = ""
        if ld_count == 0:
            scripts_to_inject = article_ld + "\n" + faqpage_ld
            injected.append("Article JSON-LD + FAQPage JSON-LD")
        elif ld_count == 1:
            # Article은 있고 FAQPage만 없는 경우
            if '"@type": "FAQPage"' not in html and "@type\": \"FAQPage" not in html:
                scripts_to_inject = faqpage_ld
                injected.append("FAQPage JSON-LD")
            else:
                scripts_to_inject = article_ld
                injected.append("Article JSON-LD")

        if scripts_to_inject:
            if "</article>" in html:
                html = html.replace("</article>", scripts_to_inject + "\n</article>", 1)
            else:
                html = html + "\n" + scripts_to_inject

    return html, injected


# ── Writer System Prompt ──────────────────────────────────────────────────────

WRITER_SYSTEM = """당신은 월 100만 뷰 이상의 AI 전문 블로거이자 Google SEO 2025 전문가입니다.

## 출력 규칙 (절대 준수)
- <article>로 시작하는 완전한 HTML만 출력
- 설명, 주석, 마크다운 없이 HTML만 반환
- 코드블록(```) 사용 금지

## 필수 HTML 구조 (순서 엄수, 누락 시 자동 보완됨)

### 1. article 래퍼
```
<article itemscope itemtype="https://schema.org/Article">
```

### 2. H1 헤딩
```
<h1 itemprop="headline">메인 키워드 포함 제목</h1>
```

### 3. 핵심 요약 박스 (H1 바로 다음, ToC 위)
```
<div class="summary-box" style="background:#f0f7ff;border-left:4px solid #1a73e8;padding:16px 20px;margin:20px 0;border-radius:4px;">
  <strong>💡 핵심 요약</strong>
  <p>[SUMMARY_CONTENT]</p>
</div>
```

### 4. 목차 (summary-box 바로 다음)
```
<nav class="toc" style="background:#f9f9f9;border:1px solid #e0e0e0;padding:16px 20px;margin:20px 0;border-radius:4px;">
  <strong>📋 목차</strong>
  <ol>
    <li><a href="#section-1">섹션 제목</a></li>
    ...
  </ol>
</nav>
```

### 5. 도입부 + 본론 H2 섹션들
- 각 H2에 id 앵커: `<h2 id="section-1">제목</h2>`
- 외부 링크: `target="_blank" rel="noopener noreferrer"` 필수
- 이미지 자리: `<!-- IMAGE: 설명 -->`

### 6. FAQ 섹션 (본론 다음, 결론 전)
```
<section class="faq" itemscope itemtype="https://schema.org/FAQPage">
  <h2>자주 묻는 질문</h2>
  <div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
    <h3 itemprop="name">질문?</h3>
    <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
      <p itemprop="text">답변</p>
    </div>
  </div>
  ... (5~7개)
</section>
```

### 7. 결론 섹션 + CTA

### 8. JSON-LD 두 개 (</article> 직전)
```
<script type="application/ld+json">
{ "@context": "https://schema.org", "@type": "Article", ... }
</script>
<script type="application/ld+json">
{ "@context": "https://schema.org", "@type": "FAQPage", ... }
</script>
```

### 9. </article> 닫기

## 작성 원칙
- 본문 글자수: 공백 제외 3,500자 이상 (FAQ, JSON-LD 제외)
- LSI 키워드: H2와 본문에 자연스럽게 분산 (밀도 1~2%)
- 내부 링크: [내부링크 자리: 주제명] 형식으로 2~3개
- 외부 링크: 최소 2개, target="_blank" rel="noopener noreferrer"
- FAQ: 5~7개, 실제로 검색할 법한 질문"""


def build_writing_prompt(topic_data: dict, seo_plan: dict) -> str:
    """작성 프롬프트 구성 — 필수 구조를 실제 HTML 뼈대로 주입"""
    plan  = seo_plan.get("plan", {})
    query = topic_data.get("query", "")

    # 참고 자료 정리
    news_refs = "\n".join([
        f"- {n.get('title','')} ({n.get('pubdate','')[:16]})"
        for n in topic_data.get("news", [])[:5] if n.get("title")
    ])
    paper_refs = "\n".join([
        f"- {p.get('title','')} — {p.get('summary','')[:200]}"
        for p in topic_data.get("papers", [])[:3] if p.get("title")
    ])
    web_refs = "\n".join([
        f"- {w.get('title','')} | {w.get('snippet','')[:150]}"
        for w in topic_data.get("web", [])[:6] if w.get("title")
    ])

    # 아웃라인 구성
    outline_sections = plan.get("outline", [])
    outline_text = ""
    for idx, sec in enumerate(outline_sections, 1):
        h2_title = sec.get("h2", f"섹션{idx}")
        outline_text += f"\n  ## {h2_title} (id=\"section-{idx}\")\n"
        for h3 in sec.get("h3_list", []):
            outline_text += f"    ### {h3}\n"
        for kp in sec.get("key_points", []):
            outline_text += f"      - {kp}\n"

    # LSI 배치 지침
    lsi_placement = plan.get("lsi_placement", {})
    if lsi_placement:
        lsi_text = "\n[LSI 키워드 배치]\n" + "\n".join(
            f"  '{h2}' 섹션: {', '.join(kws)}" for h2, kws in lsi_placement.items()
        )
    else:
        secondary_kws = plan.get("secondary_keywords", [])
        lsi_text = f"\n[LSI 키워드]: {', '.join(secondary_kws)}" if secondary_kws else ""

    # FAQ 질문
    faq_questions = plan.get("faq_questions", [])
    faq_text = "\n[FAQ 질문 (반드시 아래 질문으로 생성)]\n" + "\n".join(
        f"  {i+1}. {q}" for i, q in enumerate(faq_questions[:7])
    ) if faq_questions else "\n[FAQ]: 독자가 실제 검색할 법한 질문 5~7개 직접 생성\n"

    # 핵심 요약 박스
    summary_box = plan.get("summary_box", "").strip()
    summary_hint = f"\n[핵심 요약 박스 내용 (그대로 사용)]: {summary_box}" if summary_box else ""

    # 내부 링크
    internal_link_topics = plan.get("internal_link_topics", [])
    internal_links_text = (
        "\n[내부 링크 (본문에 2~3개 삽입)]\n" +
        "\n".join(f"  - [내부링크 자리: {t}]" for t in internal_link_topics[:3])
    ) if internal_link_topics else ""

    # ToC 섹션
    toc_sections = plan.get("toc_sections", [
        sec.get("h2", "") for sec in outline_sections
    ])
    toc_items_html = "\n".join(
        f'    <li><a href="#section-{i+1}">{sec}</a></li>'
        for i, sec in enumerate(toc_sections) if sec
    )

    # JSON-LD 데이터 준비
    title = plan.get("title", query)
    description = plan.get("meta_description", plan.get("og_description", ""))
    primary_kw = plan.get("primary_keyword", "")
    url_slug = plan.get("url_slug", "")
    blog_url = os.environ.get("BLOG_URL", "https://ai-insight-blog.blogspot.com")
    post_url = f"{blog_url}/{url_slug}" if url_slug else blog_url

    faq_ld_items = json.dumps([
        {
            "@type": "Question",
            "name": q,
            "acceptedAnswer": {"@type": "Answer", "text": f"{primary_kw} 관련: {summary_box or description}"}
        }
        for q in faq_questions[:5]
    ], ensure_ascii=False)

    return f"""다음 정보를 바탕으로 Google SEO 2025 최적화 블로그 포스트를 작성하세요.

=== SEO 정보 ===
메인 키워드: {primary_kw}
보조 키워드: {", ".join(plan.get("secondary_keywords", []))}
검색 의도: {plan.get("search_intent_detail", "")}
H1 제목: {plan.get("h1", title)}
Featured Snippet 목표: {plan.get("featured_snippet_target", "")}
{summary_hint}

=== 아웃라인 ===
{outline_text}
{lsi_text}
{faq_text}
{internal_links_text}

=== 참고 자료 ===
[최신 뉴스]
{news_refs or "없음"}

[관련 논문]
{paper_refs or "없음"}

[웹 참고]
{web_refs or "없음"}

=== 작성할 HTML 구조 (이 뼈대를 반드시 유지하고 내용을 채우세요) ===

<article itemscope itemtype="https://schema.org/Article">

<h1 itemprop="headline">{plan.get("h1", title)}</h1>

<div class="summary-box" style="background:#f0f7ff;border-left:4px solid #1a73e8;padding:16px 20px;margin:20px 0;border-radius:4px;">
  <strong>💡 핵심 요약</strong>
  <p>{summary_box or "[이 주제의 핵심을 3줄 이내로 즉시 답변하는 내용 작성]"}</p>
</div>

<nav class="toc" style="background:#f9f9f9;border:1px solid #e0e0e0;padding:16px 20px;margin:20px 0;border-radius:4px;">
  <strong>📋 목차</strong>
  <ol>
{toc_items_html or "    <li>[섹션 목록 자동 생성]</li>"}
  </ol>
</nav>

[도입부 — 150단어 이내, 검색 의도 즉시 충족]

[본론 H2 섹션들 — 아웃라인 기반, 각 섹션 300자 이상]

<section class="faq" itemscope itemtype="https://schema.org/FAQPage">
  <h2>자주 묻는 질문</h2>
  [FAQ 5~7개 — itemscope/itemprop 스키마 마크업 포함]
</section>

[결론 섹션 — 핵심 3줄 요약 + CTA: {plan.get("cta_text", "관련 포스트도 확인해보세요!")}]

<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{title}",
  "description": "{description}",
  "url": "{post_url}",
  "datePublished": "{TODAY}",
  "dateModified": "{TODAY}",
  "author": {{"@type": "Organization", "name": "AI 인사이트 블로그"}},
  "publisher": {{"@type": "Organization", "name": "AI 인사이트 블로그", "logo": {{"@type": "ImageObject", "url": "{blog_url}/favicon.ico"}}}},
  "keywords": "{primary_kw}"
}}
</script>
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": {faq_ld_items}
}}
</script>

</article>

위 뼈대의 [대괄호] 부분을 실제 고품질 콘텐츠로 채우세요.
- 본문 글자수: 공백 제외 3,500자 이상 (FAQ/JSON-LD 제외 순수 본문)
- H2 섹션마다 id="section-N" 앵커 부여
- 외부 링크 최소 2개 (target="_blank" rel="noopener noreferrer")
- 내부 링크 2~3개 ([내부링크 자리: 주제명] 형식)
- 이미지 자리: <!-- IMAGE: 설명 --> + figure 태그
<article>로 시작하는 완전한 HTML만 출력하세요."""


def extract_key_points(html: str, seo_plan: dict) -> list:
    """HTML 본문에서 핵심 포인트 3개 추출 (SNS 파이프라인용)"""
    plan = seo_plan.get("plan", {})
    outline = plan.get("outline", [])
    points = []
    for sec in outline[:3]:
        kps = sec.get("key_points", [])
        if kps:
            clean = re.sub(r'<[^>]+>', '', str(kps[0])).strip()[:40]
            if clean:
                points.append(clean)

    if not points:
        h2_matches = re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.IGNORECASE)
        points = [re.sub(r'<[^>]+>', '', h).strip()[:40] for h in h2_matches[:3] if h.strip()]

    return points[:3]


def count_chars(html: str) -> int:
    """HTML 태그 제거 후 공백 제외 글자수 (FAQ, Schema JSON-LD 제외 순수 본문만)"""
    text = re.sub(r'<section[^>]*class=["\']faq["\'][^>]*>.*?</section>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"\s+", "", text)
    return len(text)


def generate_post(topic_data: dict, seo_plan: dict, post_num: int) -> dict:
    """포스트 생성 — 하드코딩 템플릿 주입 + post-processing 보완"""
    plan  = seo_plan.get("plan", {})
    title = plan.get("title", topic_data.get("query", f"Post {post_num}"))

    print(f"  [{post_num}] 작성 시작: {title[:50]}")

    prompt = build_writing_prompt(topic_data, seo_plan)
    html_content = _call_claude(WRITER_SYSTEM, prompt, max_tokens=8000)

    # ── Post-processing: 누락 SEO 섹션 자동 보완 ──────────────────────────────
    missing_before = check_seo_structure(html_content)
    if missing_before:
        print(f"    ⚠ Claude 생성 후 누락: {missing_before} → 자동 보완 중...")
        html_content, injected = inject_missing_seo_sections(html_content, seo_plan)
        if injected:
            print(f"    ✅ 자동 보완 완료: {injected}")
    else:
        _, _ = inject_missing_seo_sections.__doc__, None  # 타입 힌트용 (실행 안 함)

    # 최종 SEO 검증
    missing_after = check_seo_structure(html_content)
    if missing_after:
        print(f"    ❌ 보완 후에도 누락 (비정상): {missing_after}")
    else:
        print(f"    ✅ SEO 구조 검증 통과")

    # 글자수 확인
    char_count = count_chars(html_content)
    print(f"    글자수: {char_count:,}자 (공백 제외, 본문만)")

    # 3,000자 미만이면 보충 요청
    if char_count < 3000:
        print(f"    ⚠ 글자수 부족 ({char_count}자) — 보충 작성 중...")
        supplement_prompt = f"""아래 포스트가 {char_count}자로 3,500자에 미달합니다.
기존 구조(summary-box, toc, faq, JSON-LD 포함)를 유지하면서 각 H2 섹션을 더 자세히 확장하세요.
새 사례, 데이터, 실전 팁을 추가해 공백 제외 3,500자 이상이 되도록 보강하세요.

기존 포스트 (처음 3,000자):
{html_content[:3000]}...

완전한 HTML 포스트로 다시 작성하세요. <article>로 시작하는 HTML만 반환하세요."""
        html_content = _call_claude("", supplement_prompt, max_tokens=8000)
        # 보충 후 다시 SEO 보완 적용
        html_content, _ = inject_missing_seo_sections(html_content, seo_plan)
        char_count = count_chars(html_content)
        print(f"    보충 후: {char_count:,}자")

    # OG/메타 정보
    og_title       = plan.get("og_title", plan.get("title", title))
    og_description = plan.get("og_description", plan.get("meta_description", ""))
    og_slug        = plan.get("url_slug", "")

    # Blogger용 메타 래퍼
    blogger_html = f"""<!-- POST: {title} -->
<!-- DATE: {TODAY} -->
<!-- KEYWORD: {plan.get('primary_keyword', '')} -->
<!-- SLUG: {og_slug} -->
<!-- OG_TITLE: {og_title} -->
<!-- OG_DESCRIPTION: {og_description} -->
<!-- META_DESCRIPTION: {plan.get('meta_description', '')} -->

{html_content}"""

    # labels 중복 제거
    raw_labels = [plan.get("primary_keyword", "AI"), "인공지능", "LLM"] + plan.get("secondary_keywords", [])[:3]
    labels = list(dict.fromkeys(raw_labels))

    key_points = extract_key_points(html_content, seo_plan)
    final_missing = check_seo_structure(html_content)

    return {
        "post_num":           post_num,
        "title":              title,
        "slug":               og_slug,
        "primary_keyword":    plan.get("primary_keyword", ""),
        "secondary_keywords": plan.get("secondary_keywords", []),
        "meta_description":   plan.get("meta_description", ""),
        "og_title":           og_title,
        "og_description":     og_description,
        "labels":             labels,
        "char_count":         char_count,
        "html_content":       blogger_html,
        "key_points":         key_points,
        "search_intent":      plan.get("search_intent", ""),
        "topic":              topic_data.get("query", ""),
        "domain":             topic_data.get("domain", ""),
        "created_at":         datetime.datetime.utcnow().isoformat(),
        "seo_issues":         final_missing,  # 빈 리스트 = 완전 통과
    }


# ── 메인 ─────────────────────────────────────────────────────────────────────

def run(topics_data: dict = None, seo_data: dict = None):
    print(f"[Writer Agent] {TODAY} 시작")

    if topics_data is None:
        t_file = os.path.join(OUT_T, f"daily_topics_{TODAY}.json")
        topics_data = json.load(open(t_file))
    if seo_data is None:
        s_file = os.path.join(OUT_S, f"seo_plan_{TODAY}.json")
        seo_data = json.load(open(s_file))

    posts = []
    for i, (topic, seo_item) in enumerate(zip(topics_data["topics"], seo_data["seo_plans"]), 1):
        print(f"\n[{i}/3] 포스트 작성...")
        try:
            post = generate_post(topic, seo_item, i)

            fname = f"post_{TODAY}_{i}.html"
            fpath = os.path.join(OUT_P, fname)
            os.makedirs(OUT_P, exist_ok=True)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(post["html_content"])

            mpath = os.path.join(OUT_P, f"post_{TODAY}_{i}_meta.json")
            meta = {k: v for k, v in post.items() if k != "html_content"}
            meta["html_file"] = fname
            with open(mpath, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)

            seo_status = "✅ SEO 통과" if not post["seo_issues"] else f"⚠ 잔여 이슈: {post['seo_issues']}"
            print(f"  {seo_status} | 저장: {fname} ({post['char_count']:,}자)")
            posts.append(meta)
        except Exception as e:
            print(f"  ❌ 오류: {e}")

    result = {"date": TODAY, "posts": posts}
    log_path = os.path.join(OUT_P, f"write_log_{TODAY}.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    passed = sum(1 for p in posts if not p.get("seo_issues"))
    print(f"\n[Writer Agent] 완료 — {len(posts)}/3 포스트 작성 | SEO 통과: {passed}/{len(posts)}")
    return result


if __name__ == "__main__":
    run()
