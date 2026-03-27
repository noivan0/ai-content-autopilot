"""
Writer Agent — P004
SEO 계획 + 리서치 자료 기반으로 3,500자 이상 블로그 포스트 작성
Google SEO 2025 최적 구조 적용
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


def _call_claude_with_retry(system: str, user: str, max_tokens: int = 8000) -> str:
    """SEO 필수 구조 검증 + 자동 재시도 (최대 2회)"""

    def check_seo(html: str) -> list:
        missing = []
        if 'class="faq"' not in html and "class='faq'" not in html:
            missing.append('FAQ 섹션 (class="faq")')
        if html.count("application/ld+json") < 2:
            missing.append(f"JSON-LD {html.count('application/ld+json')}개 (2개 필요)")
        if "summary-box" not in html:
            missing.append("핵심 요약 박스 (summary-box)")
        if 'class="toc"' not in html and "class='toc'" not in html:
            missing.append("목차 (toc)")
        return missing

    html = _call_claude(system, user, max_tokens)
    missing = check_seo(html)

    if not missing:
        return html

    # 1차 재시도
    print(f"    ⚠ SEO 누락: {missing} → 재시도 1/2")
    missing_lines = "\n".join(f"- {m} 추가 필요" for m in missing)
    retry_prompt = f"""이전 응답에서 다음 필수 SEO 요소가 누락되었습니다: {', '.join(missing)}

이전 HTML에 아래 항목을 반드시 추가해서 완전한 HTML을 다시 출력하세요:
{missing_lines}

완전한 <article>...</article> HTML을 처음부터 다시 출력하세요. 설명 없이 HTML만."""

    html2 = _call_claude(system, f"{user}\n\n{retry_prompt}", max_tokens)
    missing2 = check_seo(html2)

    if not missing2:
        print("    ✅ 재시도 1회 만에 SEO 구조 완성")
        return html2

    # 2차 재시도
    print(f"    ⚠ 여전히 누락: {missing2} → 재시도 2/2")
    missing2_lines = "\n".join(f"- {m}" for m in missing2)
    retry2 = f"""반드시 아래 구조를 포함해서 전체 HTML을 다시 작성하세요.

키워드: {user[:100]}

필수 포함 (이번에 누락되면 안 됩니다):
{missing2_lines}

<article>로 시작하는 완전한 HTML만 출력하세요."""

    html3 = _call_claude(system, retry2, max_tokens)
    missing3 = check_seo(html3)
    if missing3:
        print(f"    ⚠ 2회 재시도 후에도 누락: {missing3} (계속 진행)")
    else:
        print("    ✅ 재시도 2회 만에 SEO 구조 완성")
    return html3


# ── 작성 지침 ─────────────────────────────────────────────────────────────────

WRITER_SYSTEM = """당신은 월 100만 뷰 이상의 AI 전문 블로거이자 Google SEO 2025 전문가입니다.

## ⚠️ 절대 누락 금지 항목 (미포함 시 무효 처리)
다음 4가지가 없으면 응답 전체가 거부됩니다:
1. class="faq" 또는 class='faq' 속성을 가진 <section> 태그
2. application/ld+json 타입의 <script> 태그 2개 (Article + FAQPage)
3. class="summary-box" 를 가진 <div> 태그
4. class="toc" 를 가진 <nav> 태그

## 반드시 지켜야 할 HTML 구조 (순서 엄수)

아래 10단계 구조를 정확한 순서로 생성하세요:

1. **<article> 래퍼** — `itemscope itemtype="https://schema.org/Article"` 속성 포함
2. **H1** — `<h1 itemprop="headline">메인 키워드 포함 제목</h1>`
3. **핵심 요약 박스** — H1 바로 다음에 배치 (Featured Snippet 타겟):
   ```html
   <div class="summary-box" style="background:#f0f7ff;border-left:4px solid #1a73e8;padding:16px 20px;margin:20px 0;border-radius:4px;">
     <strong>💡 핵심 요약</strong>
     <p>3줄 이내로 검색 의도에 즉시 답변하는 내용. 독자가 이것만 읽어도 핵심을 파악할 수 있어야 함.</p>
   </div>
   ```
4. **목차(ToC)** — H2 섹션이 4개 이상일 때 자동 생성:
   ```html
   <nav class="toc" style="background:#f9f9f9;border:1px solid #e0e0e0;padding:16px 20px;margin:20px 0;border-radius:4px;">
     <strong>📋 목차</strong>
     <ol>
       <li><a href="#section-1">섹션 제목</a></li>
       <li><a href="#section-2">섹션 제목</a></li>
     </ol>
   </nav>
   ```
5. **도입부** — 150단어 이내, 검색 의도 즉시 충족, 이 글에서 얻을 것 명시
6. **본론 H2 섹션들** — 각 섹션에 `id` 앵커 부여, 각 300자 이상:
   ```html
   <h2 id="section-1">섹션 제목 (LSI 키워드 포함)</h2>
   ```
   - 불릿 목록, 표, 코드블록 적극 활용
   - 이미지 자리: `<!-- IMAGE: 설명 -->` + figure 태그
   ```html
   <!-- IMAGE: 키워드 관련 이미지 설명 -->
   <figure>
     <img alt="키워드 포함 이미지 설명" src="placeholder.jpg" loading="lazy">
     <figcaption>이미지 캡션 설명</figcaption>
   </figure>
   ```
   - 내부 링크: `[내부링크 자리: 주제명]` → `<a href="/관련-포스트">관련 포스트 제목</a>`
   - 외부 링크: 반드시 `target="_blank" rel="noopener noreferrer"` 포함
7. **FAQ 섹션** — 5~7개 Q&A (People Also Ask 타겟):
   ```html
   <section class="faq" itemscope itemtype="https://schema.org/FAQPage">
     <h2>자주 묻는 질문</h2>
     <div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
       <h3 itemprop="name">질문?</h3>
       <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
         <p itemprop="text">답변 내용</p>
       </div>
     </div>
   </section>
   ```
8. **결론** — 핵심 3줄 요약 + CTA (관련 포스트 유도, 뉴스레터 등)
9. **Article + FAQPage JSON-LD** — `</article>` 직전에 두 개 모두:
   ```html
   <script type="application/ld+json">
   { "@context": "https://schema.org", "@type": "Article", ... }
   </script>
   <script type="application/ld+json">
   { "@context": "https://schema.org", "@type": "FAQPage", ... }
   </script>
   ```
10. `</article>` 닫기

## 작성 원칙

- **글자수**: 공백 제외 3,500자 이상 (FAQ, JSON-LD 제외 순수 본문 기준)
- **LSI 키워드**: H2 헤딩과 본문에 자연스럽게 분산 배치 (키워드 밀도 1~2%)
- **내부 링크**: 최소 2~3개를 `[내부링크 자리: 주제명]` 형식으로 삽입
- **외부 링크**: 최소 2개, `target="_blank" rel="noopener noreferrer"` 필수
- **FAQ**: 독자가 실제로 검색할 법한 질문 5~7개
- **핵심 요약 박스**: 항상 H1 바로 다음, ToC 위에 배치
- **ToC**: 본문 H2를 모두 반영한 앵커 링크

출력: 완성된 HTML (Blogger 업로드용) — <article>로 시작하는 완전한 HTML만 출력"""


def build_writing_prompt(topic_data: dict, seo_plan: dict) -> str:
    """작성 프롬프트 구성"""
    query = topic_data.get("query", "")
    plan  = seo_plan.get("plan", {})

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

    # ToC 앵커와 연결된 outline 구성
    outline_sections = plan.get("outline", [])
    toc_sections = plan.get("toc_sections", [
        sec.get("h2", "") for sec in outline_sections
    ])

    outline_text = ""
    for idx, sec in enumerate(outline_sections, 1):
        anchor = f"section-{idx}"
        h2_title = sec.get("h2", toc_sections[idx-1] if idx-1 < len(toc_sections) else f"섹션{idx}")
        outline_text += f"\n  ## {h2_title} (id=\"{anchor}\")\n"
        for h3 in sec.get("h3_list", []):
            outline_text += f"    ### {h3}\n"
        for kp in sec.get("key_points", []):
            outline_text += f"      - {kp}\n"

    # LSI 배치 지침
    lsi_placement = plan.get("lsi_placement", {})
    lsi_text = ""
    if lsi_placement:
        lsi_text = "\n[LSI 키워드 배치 지침]\n"
        for h2, keywords in lsi_placement.items():
            lsi_text += f"  '{h2}' 섹션: {', '.join(keywords)}\n"
    else:
        secondary_kws = plan.get("secondary_keywords", [])
        if secondary_kws:
            lsi_text = f"\n[LSI 키워드 (본문 전체에 분산 배치)]: {', '.join(secondary_kws)}\n"

    # FAQ 질문 후보
    faq_questions = plan.get("faq_questions", [])
    faq_text = ""
    if faq_questions:
        faq_text = "\n[FAQ 질문 후보 (독자가 실제 검색할 질문)]\n"
        for i, q in enumerate(faq_questions, 1):
            faq_text += f"  {i}. {q}\n"
    else:
        faq_text = "\n[FAQ]: 이 주제와 관련해 독자가 실제로 검색할 법한 질문 5~7개를 직접 생성하세요.\n"

    # 핵심 요약 박스 힌트
    summary_box = plan.get("summary_box", "")
    summary_hint = f"\n[핵심 요약 박스 내용]: {summary_box}" if summary_box else ""

    # 내부 링크 주제
    internal_link_topics = plan.get("internal_link_topics", [])
    internal_links_text = ""
    if internal_link_topics:
        internal_links_text = "\n[내부 링크 삽입 지침] 아래 주제로 연결되는 내부 링크를 본문에 2~3개 삽입하세요:\n"
        for topic in internal_link_topics[:3]:
            internal_links_text += f"  - [내부링크 자리: {topic}]\n"

    # CTA 문구
    cta_text = plan.get("cta_text", "관련 포스트도 확인해보세요!")

    # OG 정보
    og_title = plan.get("og_title", plan.get("title", ""))
    og_description = plan.get("og_description", plan.get("meta_description", ""))

    return f"""다음 정보를 바탕으로 Google SEO 2025 최적화 블로그 포스트를 작성하세요.

=== SEO 정보 ===
메인 키워드: {plan.get("primary_keyword", query)}
보조 키워드: {", ".join(plan.get("secondary_keywords", []))}
검색 의도: {plan.get("search_intent_detail", "")}
H1 제목: {plan.get("h1", plan.get("title", query))}
Featured Snippet 목표: {plan.get("featured_snippet_target", "")}
읽기 시간: {plan.get("estimated_reading_time", "약 12분")}
{summary_hint}

=== 아웃라인 (ToC 앵커 포함) ===
{outline_text}
{lsi_text}

=== FAQ 질문 후보 ===
{faq_text}

=== 내부 링크 ===
{internal_links_text}

=== CTA ===
결론 섹션 CTA: {cta_text}

=== OG 메타 정보 (JSON-LD 참고용) ===
OG 제목: {og_title}
OG 설명: {og_description}

=== 참고 자료 ===
[최신 뉴스]
{news_refs if news_refs else "없음"}

[관련 논문]
{paper_refs if paper_refs else "없음"}

[웹 참고]
{web_refs if web_refs else "없음"}

=== 작성 요구사항 ===
1. WRITER_SYSTEM에 명시된 10단계 HTML 구조를 정확한 순서로 생성
2. 핵심 요약 박스는 H1 바로 다음, ToC 위에 배치
3. ToC에 모든 H2 섹션 앵커 링크 포함 (4개 이상 섹션이므로 필수)
4. FAQ 5~7개 (위 후보 참고하되 더 자연스럽게 작성)
5. Article JSON-LD + FAQPage JSON-LD 두 개 모두 생성
6. 공백 제외 3,500자 이상 (FAQ, JSON-LD 제외 순수 본문)
7. 각 H2 섹션 최소 300자, LSI 키워드 자연 배치
8. 외부 링크 최소 2개 (target="_blank" rel="noopener noreferrer")
9. 내부 링크 2~3개 ([내부링크 자리: 주제명] 형식)
10. 이미지 자리 <!-- IMAGE: 설명 --> + figure 태그

<article>로 시작하는 완전한 HTML만 출력하세요. 설명 텍스트 없이 HTML만 반환하세요."""


def extract_key_points(html: str, seo_plan: dict) -> list:
    """HTML 본문에서 핵심 포인트 3개 추출 (SNS 파이프라인용)"""
    # 방법 1: SEO 계획의 outline에서 각 섹션 첫 포인트 추출
    plan = seo_plan.get("plan", {})
    outline = plan.get("outline", [])
    points = []
    for sec in outline[:3]:
        kps = sec.get("key_points", [])
        if kps:
            clean = re.sub(r'<[^>]+>', '', str(kps[0])).strip()[:40]
            if clean:
                points.append(clean)

    # 방법 2: h2 태그에서 추출 (outline 없으면)
    if not points:
        h2_matches = re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.IGNORECASE)
        points = [re.sub(r'<[^>]+>', '', h).strip()[:40] for h in h2_matches[:3] if h.strip()]

    return points[:3]


def count_chars(html: str) -> int:
    """HTML 태그 제거 후 공백 제외 글자수 (FAQ, Schema JSON-LD 제외 순수 본문만)"""
    # FAQ 섹션 제거
    text = re.sub(r'<section[^>]*class=["\']faq["\'][^>]*>.*?</section>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # JSON-LD script 블록 제거
    text = re.sub(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # 나머지 HTML 태그 제거
    text = re.sub(r"<[^>]+>", "", text)
    # HTML 주석 제거
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    # 공백 제거
    text = re.sub(r"\s+", "", text)
    return len(text)


def generate_post(topic_data: dict, seo_plan: dict, post_num: int) -> dict:
    """포스트 생성"""
    plan  = seo_plan.get("plan", {})
    title = plan.get("title", topic_data.get("query", f"Post {post_num}"))

    print(f"  [{post_num}] 작성 시작: {title[:50]}")

    prompt = build_writing_prompt(topic_data, seo_plan)

    # SEO 필수 구조 자동 검증 + 재시도 로직
    html_content = _call_claude_with_retry(WRITER_SYSTEM, prompt, max_tokens=8000)

    # 글자수 확인 (FAQ, JSON-LD 제외 순수 본문)
    char_count = count_chars(html_content)
    print(f"    글자수: {char_count:,}자 (공백 제외, 본문만)")

    # SEO 구조 기본 체크 (재시도 후 최종 상태)
    seo_checks = []
    if "<h1" not in html_content:
        seo_checks.append("H1 없음")
    if "summary-box" not in html_content:
        seo_checks.append("핵심 요약 박스 없음")
    if 'class="toc"' not in html_content and "class='toc'" not in html_content:
        seo_checks.append("ToC 없음")
    if 'class="faq"' not in html_content and "class='faq'" not in html_content:
        seo_checks.append("FAQ 없음")
    if "application/ld+json" not in html_content:
        seo_checks.append("JSON-LD 없음")
    if seo_checks:
        print(f"    ⚠ SEO 구조 경고 (최종): {seo_checks}")

    # 3,000자 미만이면 보충 요청
    if char_count < 3000:
        print(f"    ⚠ 글자수 부족 ({char_count}자) — 보충 작성 중...")
        supplement_prompt = f"""아래 포스트가 {char_count}자로 3,500자에 미달합니다.
기존 구조(핵심 요약 박스, ToC, FAQ, JSON-LD 포함)를 유지하면서 각 H2 섹션을 더 자세히 확장하세요.
새 사례, 데이터, 실전 팁을 추가하고 공백 제외 3,500자 이상이 되도록 보강하세요.

기존 포스트 (처음 3,000자):
{html_content[:3000]}...

완전한 HTML 포스트로 다시 작성하세요. <article>로 시작하는 HTML만 반환하세요."""

        html_content = _call_claude("", supplement_prompt, max_tokens=8000)
        char_count   = count_chars(html_content)
        print(f"    보충 후: {char_count:,}자")

    # OG 메타 태그 주석 (Blogger 커스텀 헤더 참고용)
    og_title       = plan.get("og_title", plan.get("title", title))
    og_description = plan.get("og_description", plan.get("meta_description", ""))
    og_slug        = plan.get("url_slug", "")

    # Blogger용 메타 래퍼 추가
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
    labels = list(dict.fromkeys(raw_labels))  # 순서 유지하면서 중복 제거

    # key_points 추출 (SNS 파이프라인용)
    key_points = extract_key_points(html_content, seo_plan)

    return {
        "post_num":          post_num,
        "title":             title,
        "slug":              og_slug,
        "primary_keyword":   plan.get("primary_keyword", ""),
        "secondary_keywords": plan.get("secondary_keywords", []),
        "meta_description":  plan.get("meta_description", ""),
        "og_title":          og_title,
        "og_description":    og_description,
        "labels":            labels,
        "char_count":        char_count,
        "html_content":      blogger_html,
        "key_points":        key_points,
        "search_intent":     plan.get("search_intent", ""),
        "topic":             topic_data.get("query", ""),
        "domain":            topic_data.get("domain", ""),
        "created_at":        datetime.datetime.utcnow().isoformat(),
        "seo_checks":        seo_checks,
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

            # 파일 저장
            fname = f"post_{TODAY}_{i}.html"
            fpath = os.path.join(OUT_P, fname)
            os.makedirs(OUT_P, exist_ok=True)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(post["html_content"])

            # 메타 저장
            mpath = os.path.join(OUT_P, f"post_{TODAY}_{i}_meta.json")
            meta = {k: v for k, v in post.items() if k != "html_content"}
            meta["html_file"] = fname
            with open(mpath, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)

            print(f"  ✅ 저장: {fname} ({post['char_count']:,}자)")
            posts.append(meta)
        except Exception as e:
            print(f"  ❌ 오류: {e}")

    result = {"date": TODAY, "posts": posts}
    log_path = os.path.join(OUT_P, f"write_log_{TODAY}.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n[Writer Agent] 완료 — {len(posts)}/3 포스트 작성")
    return result


if __name__ == "__main__":
    run()
