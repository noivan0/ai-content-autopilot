"""
SEO Agent — P004
주제별 키워드 분석, 검색 의도 파악, SEO 구조 설계
Google SEO 2025 최적 기준 적용
"""
import os, json, datetime, urllib.request, urllib.error

BASE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_T  = os.path.join(BASE, "output", "topics")
OUT_S  = os.path.join(BASE, "output", "seo")
TODAY  = datetime.date.today().isoformat()

# API 설정 (내부 게이트웨이 또는 표준 Anthropic)
_api_key  = os.environ.get("ANTHROPIC_API_KEY", "")
_base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
_model    = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-5")


def _call_claude(system: str, user: str, max_tokens: int = 3000) -> str:
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


# ── SEO 분석 프롬프트 ─────────────────────────────────────────────────────────

SEO_SYSTEM = """당신은 구글 SEO 전문가이자 AI 분야 콘텐츠 전략가입니다.
한국어 구글 검색 최적화에 특화되어 있으며, 검색 의도 분석과 E-E-A-T 기반 콘텐츠 설계가 전문입니다.
규칙: 오직 유효한 JSON만 반환하세요. 설명, 주석, 마크다운 없이 JSON 객체만 출력하세요."""


def analyze_seo(topic_data: dict) -> dict:
    """Claude로 SEO 구조 설계"""
    query = topic_data["query"]
    news_titles  = [n.get("title","") for n in topic_data.get("news",[])[:3]]
    paper_titles = [p.get("title","") for p in topic_data.get("papers",[])[:2]]
    web_snippets = [w.get("snippet","") for w in topic_data.get("web",[])[:5]]

    prompt = f"""다음 AI 관련 주제에 대한 구글 SEO 최적화 계획을 JSON으로 작성하세요.

주제: {query}

수집된 뉴스 제목:
{chr(10).join(f"- {t}" for t in news_titles if t)}

관련 논문 제목:
{chr(10).join(f"- {t}" for t in paper_titles if t)}

웹 검색 스니펫:
{chr(10).join(f"- {s[:150]}" for s in web_snippets if s)}

아래 JSON 구조로 정확히 응답하세요:
{{
  "primary_keyword": "메인 타겟 키워드 (검색량 높은 것)",
  "secondary_keywords": ["LSI 키워드 1", "LSI 키워드 2", "LSI 키워드 3", "LSI 키워드 4", "LSI 키워드 5"],
  "search_intent": "정보습득|비교|방법|최신동향 중 하나",
  "search_intent_detail": "이 키워드를 검색하는 사용자의 구체적인 의도 설명 (2~3문장)",
  "title": "클릭률 높은 포스트 제목 (55자 이내, 키워드 포함)",
  "meta_description": "검색 결과에 표시될 설명 (120~155자, 키워드+가치 포함)",
  "url_slug": "url-friendly-slug-in-english-with-hyphens",
  "h1": "H1 헤딩 (제목과 유사하되 약간 다르게, 메인 키워드 포함)",
  "outline": [
    {{
      "h2": "H2 헤딩 (LSI 키워드 포함)",
      "h3_list": ["H3 소제목1", "H3 소제목2"],
      "key_points": ["이 섹션에서 다룰 핵심 내용"]
    }}
  ],
  "featured_snippet_target": "구글 Featured Snippet 노리는 질문 + 간단 답변 형식",
  "faq_questions": [
    "FAQ 질문1? (독자가 실제로 검색할 법한 질문)",
    "FAQ 질문2?",
    "FAQ 질문3?",
    "FAQ 질문4?",
    "FAQ 질문5?",
    "FAQ 질문6?",
    "FAQ 질문7?"
  ],
  "summary_box": "핵심 요약 박스에 넣을 3줄 이내 즉시 답변. 검색 의도에 바로 답하는 내용.",
  "toc_sections": ["섹션1 제목 (outline H2와 일치)", "섹션2 제목", "섹션3 제목", "섹션4 제목", "섹션5 제목"],
  "lsi_placement": {{
    "H2 헤딩1": ["배치할 LSI 키워드1", "LSI 키워드2"],
    "H2 헤딩2": ["LSI 키워드3", "LSI 키워드4"]
  }},
  "cta_text": "결론 CTA 문구 (독자 행동 유도, 관련 포스트 또는 뉴스레터 등)",
  "og_title": "Open Graph 제목 (소셜 공유용, 60자 이내)",
  "og_description": "Open Graph 설명 (소셜 공유용, 120자 이내)",
  "internal_link_topics": ["연결할 관련 포스트 주제 1", "연결할 관련 포스트 주제 2", "연결할 관련 포스트 주제 3"],
  "target_word_count": 3500,
  "estimated_reading_time": "읽기 소요 시간 (예: 약 12분)"
}}

중요:
- outline H2 섹션은 최소 5개 이상
- faq_questions는 반드시 5개 이상 (최대 7개)
- meta_description은 120~155자 범위
- toc_sections와 outline의 H2가 일치해야 함
- lsi_placement는 각 H2 섹션에 배치할 LSI 키워드를 매핑

위 JSON 구조를 그대로 채워서 반환하세요. 설명 없이 JSON 객체만 출력하세요."""

    raw = _call_claude(SEO_SYSTEM, prompt, max_tokens=4096)

    # JSON 추출 — 여러 방식 순차 시도 (강건화)
    def extract_json(text: str) -> dict:
        import re

        candidates = []

        # 1. ```json ... ``` 코드블록
        for m in re.finditer(r"```json\s*([\s\S]*?)```", text):
            candidates.append(m.group(1).strip())

        # 2. ``` ... ``` 코드블록 (언어 미지정)
        for m in re.finditer(r"```\s*([\s\S]*?)```", text):
            candidates.append(m.group(1).strip())

        # 3. 가장 바깥쪽 { ... } 추출 (중첩 중괄호 균형 맞추기)
        start = text.find("{")
        if start != -1:
            depth = 0
            end = start
            for idx, ch in enumerate(text[start:], start):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = idx + 1
                        break
            if end > start:
                candidates.append(text[start:end])

        # 각 후보에 대해 파싱 시도
        for candidate in candidates:
            # 시도 A: 원본 그대로
            try:
                return json.loads(candidate)
            except Exception:
                pass

            # 시도 B: 후행 쉼표 제거 (,} / ,])
            cleaned = re.sub(r",\s*([}\]])", r"\1", candidate)
            try:
                return json.loads(cleaned)
            except Exception:
                pass

            # 시도 C: 제어 문자 제거 후 재시도
            cleaned2 = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", cleaned)
            try:
                return json.loads(cleaned2)
            except Exception:
                pass

        # 최후 수단: 잘린 JSON 복구 시도 (중괄호 균형 맞추기)
        for candidate in candidates[:1]:  # 가장 첫 번째 후보만
            try:
                # 열린 괄호/따옴표 수를 세어 강제로 닫기
                fixed = candidate.rstrip().rstrip(",")
                # 닫히지 않은 문자열 처리
                if fixed.count('"') % 2 == 1:
                    fixed += '"'
                # 닫히지 않은 배열/객체 처리
                open_brackets = fixed.count("[") - fixed.count("]")
                open_braces   = fixed.count("{") - fixed.count("}")
                fixed += "]" * max(0, open_brackets)
                fixed += "}" * max(0, open_braces)
                result = json.loads(fixed)
                print(f"    ⚠ JSON 잘림 감지 — 복구 성공 (필드 일부 누락 가능)")
                return result
            except Exception:
                pass

        print(f"    ⚠ JSON 파싱 실패 — raw 앞 200자: {text[:200]!r}")
        return {}

    return extract_json(raw)


def check_seo_quality(seo_plan: dict) -> list:
    """SEO 체크리스트 검증 (2025 기준 강화)"""
    issues = []
    title  = seo_plan.get("title", "")
    meta   = seo_plan.get("meta_description", "")
    pk     = seo_plan.get("primary_keyword", "")

    # 제목 길이 (60자 이내 권장)
    if len(title) > 60:
        issues.append(f"제목 너무 김 ({len(title)}자 > 60자)")

    # 메타 설명 길이 (120~155자 권장)
    meta_len = len(meta)
    if meta_len < 120:
        issues.append(f"메타 설명 너무 짧음 ({meta_len}자 < 120자 권장)")
    elif meta_len > 155:
        issues.append(f"메타 설명 너무 김 ({meta_len}자 > 155자 권장)")

    # 메인 키워드 제목 포함
    if pk and pk not in title:
        issues.append(f"메인 키워드 '{pk}'가 제목에 없음")

    # 아웃라인 섹션 수 (최소 5개)
    outline = seo_plan.get("outline", [])
    if len(outline) < 5:
        issues.append(f"아웃라인 H2 섹션 부족 ({len(outline)}개 < 5개 권장)")

    # FAQ 질문 수 (최소 5개)
    faq_questions = seo_plan.get("faq_questions", [])
    if len(faq_questions) < 5:
        issues.append(f"FAQ 질문 부족 ({len(faq_questions)}개 < 5개 필수)")

    # 핵심 요약 박스 존재 여부
    if not seo_plan.get("summary_box", "").strip():
        issues.append("핵심 요약 박스(summary_box) 없음")

    # OG 태그 확인
    if not seo_plan.get("og_title", ""):
        issues.append("og_title 없음")
    if not seo_plan.get("og_description", ""):
        issues.append("og_description 없음")

    # ToC 섹션 확인
    toc_sections = seo_plan.get("toc_sections", [])
    if len(toc_sections) < 4:
        issues.append(f"toc_sections 부족 ({len(toc_sections)}개 < 4개 권장)")

    # URL slug 확인 (영문+하이픈)
    slug = seo_plan.get("url_slug", "")
    if slug and not all(c.isalnum() or c == '-' for c in slug):
        issues.append(f"url_slug에 허용되지 않는 문자 포함: {slug}")

    return issues


# ── 메인 ─────────────────────────────────────────────────────────────────────

def run(topics_data: dict = None):
    print(f"[SEO Agent] {TODAY} 시작")

    # 리서치 결과 로드
    if topics_data is None:
        topic_file = os.path.join(OUT_T, f"daily_topics_{TODAY}.json")
        if not os.path.exists(topic_file):
            raise FileNotFoundError(f"리서치 파일 없음: {topic_file}")
        topics_data = json.load(open(topic_file))

    output_path = os.path.join(OUT_S, f"seo_plan_{TODAY}.json")

    seo_plans = []
    for i, topic in enumerate(topics_data["topics"], 1):
        print(f"\n  [{i}/3] SEO 분석: {topic['query']}")
        try:
            plan = analyze_seo(topic)
            issues = check_seo_quality(plan)
            if issues:
                print(f"    ⚠ SEO 이슈: {issues}")
            else:
                print(f"    ✅ SEO 체크 통과")
            print(f"    제목: {plan.get('title','')}")
            print(f"    키워드: {plan.get('primary_keyword','')} | 의도: {plan.get('search_intent','')}")
            print(f"    FAQ: {len(plan.get('faq_questions',[]))}개 | 섹션: {len(plan.get('outline',[]))}개")
            seo_plans.append({"topic": topic["query"], "plan": plan, "issues": issues})
        except Exception as e:
            print(f"    ❌ 오류: {e}")
            seo_plans.append({"topic": topic["query"], "plan": {}, "issues": [str(e)]})

    result = {"date": TODAY, "seo_plans": seo_plans}
    os.makedirs(OUT_S, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n[SEO Agent] 완료 → {output_path}")
    return result


if __name__ == "__main__":
    run()
