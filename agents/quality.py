"""
Content Quality Module — P005
콘텐츠 품질 자동 평가 + 향상 유틸리티

## 품질 점수 체계 (100점 만점)
- SEO 구조 (30점): H1/summary-box/toc/FAQ/JSON-LD
- 콘텐츠 깊이 (25점): 글자수, 섹션 수, 외부 링크
- 가독성 (20점): 문단 길이, 리스트/표 활용, 이미지
- E-E-A-T (15점): 출처 인용, 날짜, 전문 용어
- 검색 의도 충족 (10점): Featured Snippet 구조, FAQ 품질

변경 이력:
- v1 (2026-03-30): 초기 구현
"""

import re
import json


# ── 품질 점수 계산 ──────────────────────────────────────────────────────────────

def score_seo_structure(html: str) -> tuple[int, list]:
    """SEO 구조 점수 (30점 만점)"""
    score = 0
    notes = []

    checks = [
        ("<h1", 5, "H1 헤딩"),
        ("summary-box", 7, "핵심 요약 박스"),
        ('class="toc"', 6, "목차(ToC)"),
        ('class="faq"', 7, "FAQ 섹션"),
        ("application/ld+json", 5, "JSON-LD"),
    ]
    for pattern, pts, label in checks:
        if pattern in html:
            score += pts
        else:
            notes.append(f"❌ {label} 없음 (-{pts}점)")

    # JSON-LD 2개 여부 (보너스)
    ld_count = html.count("application/ld+json")
    if ld_count >= 2:
        score = min(score + 0, 30)  # 기본 포함
    elif ld_count == 1:
        notes.append("⚠ JSON-LD 1개 (Article + FAQPage 둘 다 필요)")

    return min(score, 30), notes


def score_content_depth(html: str, char_count: int) -> tuple[int, list]:
    """콘텐츠 깊이 점수 (25점 만점)"""
    score = 0
    notes = []

    # 글자수 (10점)
    if char_count >= 4000:
        score += 10
    elif char_count >= 3500:
        score += 8
        notes.append(f"⚠ 글자수 {char_count:,}자 (4,000자 이상 권장)")
    elif char_count >= 3000:
        score += 5
        notes.append(f"⚠ 글자수 {char_count:,}자 (3,500자+ 목표)")
    else:
        notes.append(f"❌ 글자수 부족 ({char_count:,}자 < 3,000자)")

    # H2 섹션 수 (5점)
    h2_count = len(re.findall(r'<h2[^>]*>', html, re.IGNORECASE))
    if h2_count >= 5:
        score += 5
    elif h2_count >= 4:
        score += 3
        notes.append(f"⚠ H2 섹션 {h2_count}개 (5개 이상 권장)")
    else:
        notes.append(f"❌ H2 섹션 부족 ({h2_count}개)")

    # 외부 링크 (5점)
    ext_links = html.count('target="_blank"')
    if ext_links >= 3:
        score += 5
    elif ext_links >= 2:
        score += 3
        notes.append(f"⚠ 외부 링크 {ext_links}개 (3개 이상 권장)")
    else:
        score += 1
        notes.append(f"❌ 외부 링크 부족 ({ext_links}개 < 2개)")

    # 내부 링크 (5점)
    int_links = len(re.findall(r'href=["\']/', html)) + len(re.findall(r'\[내부링크 자리', html))
    if int_links >= 3:
        score += 5
    elif int_links >= 2:
        score += 3
        notes.append(f"⚠ 내부 링크 {int_links}개 (3개 이상 권장)")
    else:
        notes.append(f"❌ 내부 링크 부족 ({int_links}개 < 2개)")

    return min(score, 25), notes


def score_readability(html: str) -> tuple[int, list]:
    """가독성 점수 (20점 만점)"""
    score = 0
    notes = []

    # 리스트 활용 (5점)
    ul_count = len(re.findall(r'<ul', html, re.IGNORECASE))
    ol_count = len(re.findall(r'<ol', html, re.IGNORECASE))
    list_count = ul_count + ol_count
    if list_count >= 4:
        score += 5
    elif list_count >= 2:
        score += 3
        notes.append(f"⚠ 리스트 {list_count}개 (4개 이상 권장)")
    else:
        notes.append(f"❌ 리스트 부족 ({list_count}개)")

    # 표 활용 (3점)
    table_count = len(re.findall(r'<table', html, re.IGNORECASE))
    if table_count >= 1:
        score += 3
    else:
        notes.append("⚠ 표(table) 없음 (비교/스펙 정리에 활용 권장)")

    # 이미지/figure (4점)
    img_count = len(re.findall(r'<img|<figure|<!-- IMAGE', html, re.IGNORECASE))
    if img_count >= 3:
        score += 4
    elif img_count >= 1:
        score += 2
        notes.append(f"⚠ 이미지 {img_count}개 (3개 이상 권장)")
    else:
        notes.append("❌ 이미지 없음")

    # 문단 길이 (4점) — 너무 긴 단일 문단 체크
    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE)
    long_paras = [p for p in paragraphs if len(re.sub(r'<[^>]+>', '', p)) > 400]
    if len(long_paras) == 0:
        score += 4
    elif len(long_paras) <= 2:
        score += 2
        notes.append(f"⚠ 긴 문단 {len(long_paras)}개 (400자 초과 문단은 분리 권장)")
    else:
        notes.append(f"❌ 긴 문단 {len(long_paras)}개 (가독성 저하)")

    # H3 소제목 활용 (4점)
    h3_count = len(re.findall(r'<h3', html, re.IGNORECASE))
    if h3_count >= 4:
        score += 4
    elif h3_count >= 2:
        score += 2
        notes.append(f"⚠ H3 {h3_count}개 (섹션당 1~2개 권장)")
    else:
        notes.append(f"⚠ H3 부족 ({h3_count}개)")

    return min(score, 20), notes


def score_eeat(html: str, meta: dict) -> tuple[int, list]:
    """E-E-A-T 점수 (15점 만점)"""
    score = 0
    notes = []

    # 날짜 명시 (3점)
    date_patterns = [r'202[4-9]', r'pubdate', r'datePublished', r'작성일', r'업데이트']
    if any(re.search(p, html, re.IGNORECASE) for p in date_patterns):
        score += 3
    else:
        notes.append("⚠ 날짜 정보 없음 (E-E-A-T 신뢰도 저하)")

    # 출처/인용 (4점)
    source_patterns = [r'출처:', r'참고:', r'ref\.', r'according to', r'연구에 따르면', r'arxiv', r'github']
    source_count = sum(1 for p in source_patterns if re.search(p, html, re.IGNORECASE))
    if source_count >= 3:
        score += 4
    elif source_count >= 1:
        score += 2
        notes.append(f"⚠ 출처 인용 {source_count}개 (3개 이상 권장)")
    else:
        notes.append("❌ 출처/인용 없음 (E-E-A-T 핵심 요소)")

    # 전문 용어 활용 (4점)
    tech_terms = ['API', 'LLM', '토큰', '파라미터', '벤치마크', '모델', '아키텍처', '파인튜닝', '추론', '임베딩']
    term_count = sum(1 for t in tech_terms if t in html)
    if term_count >= 6:
        score += 4
    elif term_count >= 3:
        score += 2
    else:
        notes.append("⚠ 전문 용어 활용 부족")

    # Author/Publisher Schema (4점)
    if '"author"' in html or '"publisher"' in html:
        score += 4
    else:
        notes.append("⚠ Author/Publisher Schema 없음")

    return min(score, 15), notes


def score_search_intent(html: str, seo_plan: dict) -> tuple[int, list]:
    """검색 의도 충족 점수 (10점 만점)"""
    score = 0
    notes = []
    plan = seo_plan.get("plan", {})

    # Featured Snippet 구조 (summary-box 내 즉시 답변, 4점)
    if "summary-box" in html:
        summary_match = re.search(r'class="summary-box"[^>]*>.*?<p>(.*?)</p>', html, re.DOTALL)
        if summary_match:
            summary_len = len(re.sub(r'<[^>]+>', '', summary_match.group(1)))
            if 50 <= summary_len <= 300:
                score += 4
            else:
                score += 2
                notes.append(f"⚠ 핵심 요약 길이 {summary_len}자 (50~300자 권장)")
        else:
            score += 1

    # FAQ 질 (6점) — 질문 수 + 답변 길이
    faq_questions = re.findall(r'itemprop="name">(.*?)</h3>', html, re.DOTALL)
    faq_answers   = re.findall(r'itemprop="text">(.*?)</p>', html, re.DOTALL)

    if len(faq_questions) >= 5:
        score += 3
    elif len(faq_questions) >= 3:
        score += 2
        notes.append(f"⚠ FAQ {len(faq_questions)}개 (5개 이상 권장)")
    else:
        notes.append(f"❌ FAQ 부족 ({len(faq_questions)}개)")

    if faq_answers:
        avg_len = sum(len(re.sub(r'<[^>]+>', '', a)) for a in faq_answers) / len(faq_answers)
        if avg_len >= 80:
            score += 3
        elif avg_len >= 40:
            score += 1
            notes.append(f"⚠ FAQ 답변 평균 {avg_len:.0f}자 (80자 이상 권장)")
        else:
            notes.append(f"❌ FAQ 답변 너무 짧음 (평균 {avg_len:.0f}자)")

    return min(score, 10), notes


def evaluate_quality(html: str, meta: dict, seo_plan: dict) -> dict:
    """
    콘텐츠 품질 종합 평가.
    반환: {score, grade, breakdown, all_notes, recommendations}
    """
    char_count = meta.get("char_count", 0)

    s1, n1 = score_seo_structure(html)
    s2, n2 = score_content_depth(html, char_count)
    s3, n3 = score_readability(html)
    s4, n4 = score_eeat(html, meta)
    s5, n5 = score_search_intent(html, seo_plan)

    total = s1 + s2 + s3 + s4 + s5
    all_notes = n1 + n2 + n3 + n4 + n5

    if total >= 90:
        grade = "S"
    elif total >= 80:
        grade = "A"
    elif total >= 70:
        grade = "B"
    elif total >= 60:
        grade = "C"
    else:
        grade = "D"

    # 개선 권고 (점수 낮은 항목 우선)
    recommendations = []
    if s1 < 25:
        recommendations.append("🔴 SEO 구조 보완 필요 (자동 보완 적용 확인)")
    if s2 < 20:
        recommendations.append("🟡 콘텐츠 분량 확대 또는 외부/내부 링크 추가")
    if s3 < 15:
        recommendations.append("🟡 가독성 개선: 리스트/표 추가, 긴 문단 분리")
    if s4 < 10:
        recommendations.append("🟠 E-E-A-T 강화: 출처 인용, 날짜, Author Schema 추가")
    if s5 < 7:
        recommendations.append("🟠 검색 의도 충족: 핵심 요약 박스 및 FAQ 품질 개선")

    return {
        "score": total,
        "grade": grade,
        "breakdown": {
            "seo_structure":   {"score": s1, "max": 30},
            "content_depth":   {"score": s2, "max": 25},
            "readability":     {"score": s3, "max": 20},
            "eeat":            {"score": s4, "max": 15},
            "search_intent":   {"score": s5, "max": 10},
        },
        "all_notes": all_notes,
        "recommendations": recommendations,
    }


# ── 품질 보고서 출력 ──────────────────────────────────────────────────────────

def print_quality_report(post_num: int, title: str, result: dict):
    grade = result["grade"]
    score = result["score"]
    bd = result["breakdown"]

    grade_emoji = {"S": "🏆", "A": "⭐", "B": "✅", "C": "⚠️", "D": "❌"}.get(grade, "")
    print(f"\n  [{post_num}] {grade_emoji} 품질: {grade}등급 ({score}/100점) — {title[:40]}")
    print(f"       SEO구조:{bd['seo_structure']['score']}/30 | "
          f"콘텐츠:{bd['content_depth']['score']}/25 | "
          f"가독성:{bd['readability']['score']}/20 | "
          f"E-E-A-T:{bd['eeat']['score']}/15 | "
          f"검색의도:{bd['search_intent']['score']}/10")

    for note in result["all_notes"][:5]:  # 최대 5개만 표시
        print(f"       {note}")
    for rec in result["recommendations"]:
        print(f"       → {rec}")


def run_quality_check(write_data: dict, seo_data: dict) -> dict:
    """
    전체 포스트 품질 평가 실행.
    반환: {date, results, summary}
    """
    import os
    import datetime

    TODAY = datetime.date.today().isoformat()
    BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    OUT_P_DIR = os.path.join(BASE, "output", "posts")
    OUT_L_DIR = os.path.join(BASE, "output", "logs")
    os.makedirs(OUT_L_DIR, exist_ok=True)

    posts     = write_data.get("posts", [])
    seo_plans = seo_data.get("seo_plans", []) if seo_data else []

    # seo_plan을 post_num으로 매핑
    seo_map = {i+1: sp for i, sp in enumerate(seo_plans)}

    quality_results = []
    for post_meta in posts:
        post_num  = post_meta.get("post_num", 1)
        title     = post_meta.get("title", "")
        html_file = os.path.join(OUT_P_DIR, post_meta.get("html_file", f"post_{TODAY}_{post_num}.html"))

        if not os.path.exists(html_file):
            print(f"  [{post_num}] ⚠ HTML 파일 없음 — 품질 평가 스킵")
            continue

        html      = open(html_file, encoding="utf-8").read()
        seo_plan  = seo_map.get(post_num, {})
        result    = evaluate_quality(html, post_meta, seo_plan)

        print_quality_report(post_num, title, result)
        quality_results.append({
            "post_num":      post_num,
            "title":         title,
            **result,
        })

    # 요약
    if quality_results:
        avg_score = sum(r["score"] for r in quality_results) / len(quality_results)
        grades    = [r["grade"] for r in quality_results]
        summary = {
            "avg_score": round(avg_score, 1),
            "grades":    grades,
            "total":     len(quality_results),
            "s_count":   grades.count("S"),
            "a_count":   grades.count("A"),
            "b_count":   grades.count("B"),
            "c_count":   grades.count("C") + grades.count("D"),
        }
        print(f"\n  품질 요약: 평균 {avg_score:.1f}점 | 등급: {' / '.join(grades)}")
    else:
        summary = {"avg_score": 0, "grades": [], "total": 0}

    result_data = {"date": TODAY, "results": quality_results, "summary": summary}

    # 저장
    log_path = os.path.join(OUT_L_DIR, f"quality_report_{TODAY}.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    return result_data
