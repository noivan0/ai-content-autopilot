"""
Analytics Agent — P004
Google Search Console API로 성과 추적 + 주간 리포트
개선: 포스트-쿼리 매핑, 포스트별 성과 섹션, CTR 개선 제안
"""
import os, json, datetime, urllib.request, urllib.parse, glob

BASE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_L  = os.path.join(BASE, "output", "logs")
OUT_P  = os.path.join(BASE, "output", "posts")

SITE_URL      = os.environ.get("GSC_SITE_URL", "")       # https://yourblog.blogspot.com/
ACCESS_TOKEN  = os.environ.get("BLOGGER_ACCESS_TOKEN", "")


def gsc_query(start_date: str, end_date: str, dimensions=None, row_limit=50) -> dict:
    """Google Search Console API 쿼리"""
    if not SITE_URL or not ACCESS_TOKEN:
        raise ValueError("GSC_SITE_URL / BLOGGER_ACCESS_TOKEN 환경변수 필요")

    url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{urllib.parse.quote(SITE_URL, safe='')}/searchAnalytics/query"

    payload = {
        "startDate":     start_date,
        "endDate":       end_date,
        "dimensions":    dimensions or ["query"],
        "rowLimit":      row_limit,
        "dataState":     "final",
    }

    data = json.dumps(payload).encode()
    req  = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type":  "application/json",
    }, method="POST")

    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def get_top_queries(start_date: str, end_date: str) -> list:
    """상위 검색 쿼리 수집"""
    try:
        data = gsc_query(start_date, end_date, dimensions=["query"], row_limit=50)
        rows = data.get("rows", [])
        return [{
            "query":       r.get("keys", [""])[0],
            "clicks":      r.get("clicks", 0),
            "impressions": r.get("impressions", 0),
            "ctr":         round(r.get("ctr", 0) * 100, 2),
            "position":    round(r.get("position", 0), 1),
        } for r in rows]
    except Exception as e:
        print(f"  [GSC ERR] {e}")
        return []


def get_page_performance(start_date: str, end_date: str) -> list:
    """페이지별 성과"""
    try:
        data = gsc_query(start_date, end_date, dimensions=["page"], row_limit=30)
        rows = data.get("rows", [])
        return [{
            "url":         r.get("keys", [""])[0],
            "clicks":      r.get("clicks", 0),
            "impressions": r.get("impressions", 0),
            "ctr":         round(r.get("ctr", 0) * 100, 2),
            "position":    round(r.get("position", 0), 1),
        } for r in rows]
    except Exception as e:
        print(f"  [GSC ERR] {e}")
        return []


def get_post_query_mapping(pages: list, posts_dir: str = None) -> list:
    """GSC 페이지 데이터와 로컬 _meta.json을 URL 기반으로 매핑
    
    Args:
        pages: get_page_performance() 결과 (url 포함)
        posts_dir: _meta.json 파일이 있는 디렉토리 (기본값: OUT_P)
    
    Returns:
        매핑된 포스트별 성과 리스트
    """
    if posts_dir is None:
        posts_dir = OUT_P

    # 로컬 메타 파일 로드
    meta_files = glob.glob(os.path.join(posts_dir, "*_meta.json"))
    local_posts = {}
    for mf in meta_files:
        try:
            meta = json.load(open(mf, encoding="utf-8"))
            slug = meta.get("slug", "")
            title = meta.get("title", "")
            primary_kw = meta.get("primary_keyword", "")
            if slug:
                local_posts[slug] = {
                    "title": title,
                    "primary_keyword": primary_kw,
                    "meta_file": os.path.basename(mf),
                    "char_count": meta.get("char_count", 0),
                    "created_at": meta.get("created_at", ""),
                }
        except Exception as e:
            print(f"  [META ERR] {mf}: {e}")

    # URL 기반 매핑
    mapped = []
    for page in pages:
        url = page.get("url", "")
        # URL에서 slug 추출 (마지막 경로 세그먼트, .html 제거)
        slug_candidate = url.rstrip("/").split("/")[-1].replace(".html", "")

        matched_meta = local_posts.get(slug_candidate, {})

        mapped.append({
            "url":             url,
            "slug":            slug_candidate,
            "title":           matched_meta.get("title", ""),
            "primary_keyword": matched_meta.get("primary_keyword", ""),
            "char_count":      matched_meta.get("char_count", 0),
            "clicks":          page.get("clicks", 0),
            "impressions":     page.get("impressions", 0),
            "ctr":             page.get("ctr", 0),
            "position":        page.get("position", 0),
            "matched":         bool(matched_meta),
        })

    # 클릭 수 내림차순 정렬
    mapped.sort(key=lambda x: -x.get("clicks", 0))
    return mapped


def get_improvement_suggestions(pages: list) -> list:
    """CTR < 3%이고 노출 > 50인 포스트에 대한 개선 제안 생성
    
    Args:
        pages: get_page_performance() 또는 get_post_query_mapping() 결과
    
    Returns:
        개선 제안 텍스트 리스트
    """
    suggestions = []
    low_ctr_pages = [
        p for p in pages
        if p.get("ctr", 0) < 3.0 and p.get("impressions", 0) > 50
    ]
    # 노출 많은 순으로 정렬
    low_ctr_pages.sort(key=lambda x: -x.get("impressions", 0))

    for p in low_ctr_pages[:10]:
        url        = p.get("url", "")
        title      = p.get("title", url.split("/")[-1])
        ctr        = p.get("ctr", 0)
        impressions = p.get("impressions", 0)
        position   = p.get("position", 0)
        primary_kw = p.get("primary_keyword", "")

        # 순위에 따른 제안
        if position <= 3:
            action = "제목/메타 설명 A/B 테스트 (순위는 높으나 CTR 저조 → 클릭 유인 문구 개선)"
        elif position <= 10:
            action = "제목에 숫자/연도 추가, 메타 설명에 감성 트리거 추가 (예: '완벽 가이드', '2025 최신')"
        else:
            action = "콘텐츠 보강으로 순위 상승 우선 (현재 {:.1f}위 → 10위 이내 진입 목표)".format(position)

        kw_hint = f" | 키워드: {primary_kw}" if primary_kw else ""
        suggestions.append(
            f"[CTR {ctr}% / 노출 {impressions:,}회 / {position:.1f}위{kw_hint}] "
            f"{title[:40]}: {action}"
        )

    return suggestions


def build_weekly_report(week_start: str, week_end: str) -> str:
    """주간 마크다운 리포트 생성"""
    print(f"  기간: {week_start} ~ {week_end}")

    queries = get_top_queries(week_start, week_end)
    pages   = get_page_performance(week_start, week_end)

    total_clicks      = sum(q.get("clicks", 0) for q in queries)
    total_impressions = sum(q.get("impressions", 0) for q in queries)
    avg_ctr           = round(total_clicks / total_impressions * 100, 2) if total_impressions > 0 else 0
    avg_position      = round(sum(q.get("position", 0) for q in queries) / len(queries), 1) if queries else 0

    # 고성과 쿼리 (CTR > 5%)
    high_ctr = [q for q in queries if q.get("ctr", 0) > 5.0]
    # 노출 많은데 CTR 낮은 쿼리 (개선 필요)
    low_ctr  = sorted([q for q in queries if q.get("impressions", 0) > 100 and q.get("ctr", 0) < 3.0],
                      key=lambda x: -x.get("impressions", 0))[:5]

    # 포스트-쿼리 매핑
    post_mapping = get_post_query_mapping(pages)
    improvement_suggestions = get_improvement_suggestions(post_mapping)

    md = f"""# P004 주간 성과 리포트
**기간**: {week_start} ~ {week_end}
**생성일**: {datetime.date.today().isoformat()}

---

## 전체 요약

| 지표 | 수치 |
|------|------|
| 총 클릭수 | {total_clicks:,} |
| 총 노출수 | {total_impressions:,} |
| 평균 CTR | {avg_ctr}% |
| 평균 순위 | {avg_position}위 |

---

## 상위 검색 쿼리 (클릭순)

| 검색어 | 클릭 | 노출 | CTR | 순위 |
|--------|------|------|-----|------|
"""
    for q in queries[:10]:
        md += f"| {q['query'][:40]} | {q['clicks']} | {q['impressions']:,} | {q['ctr']}% | {q['position']} |\n"

    md += f"""
---

## 상위 페이지 성과

| URL | 클릭 | 노출 | CTR | 순위 |
|-----|------|------|-----|------|
"""
    for p in pages[:10]:
        url_short = p["url"].replace(SITE_URL, "")[:50]
        md += f"| {url_short} | {p['clicks']} | {p['impressions']:,} | {p['ctr']}% | {p['position']} |\n"

    # ── 포스트별 성과 섹션 ──────────────────────────────────────────────────────
    md += f"""
---

## 포스트별 성과 (로컬 메타 매핑)

| 포스트 제목 | 키워드 | 클릭 | 노출 | CTR | 순위 | 글자수 |
|------------|--------|------|------|-----|------|--------|
"""
    for pm in post_mapping[:10]:
        title_short = (pm.get("title") or pm.get("slug") or "")[:35]
        kw_short    = pm.get("primary_keyword", "")[:15]
        char_count  = pm.get("char_count", 0)
        char_str    = f"{char_count:,}자" if char_count else "-"
        md += f"| {title_short} | {kw_short} | {pm['clicks']} | {pm['impressions']:,} | {pm['ctr']}% | {pm['position']} | {char_str} |\n"

    # ── 개선 제안 섹션 ──────────────────────────────────────────────────────────
    md += f"""
---

## CTR 개선 필요 포스트 (노출 > 50, CTR < 3%)
"""
    if improvement_suggestions:
        for suggestion in improvement_suggestions:
            md += f"- {suggestion}\n"
    else:
        md += "- 해당 없음\n"

    md += f"""
---

## 고성과 키워드 (CTR > 5%)
"""
    if high_ctr:
        for q in high_ctr[:5]:
            md += f"- **{q['query']}**: CTR {q['ctr']}%, 순위 {q['position']}위\n"
    else:
        md += "- 해당 없음\n"

    md += f"""
---

## 개선 필요 검색쿼리 (노출 많은데 CTR 낮음)
"""
    if low_ctr:
        for q in low_ctr:
            md += f"- **{q['query']}**: 노출 {q['impressions']:,}, CTR {q['ctr']}% → 제목/메타 개선 필요\n"
    else:
        md += "- 해당 없음\n"

    md += f"""
---

## 다음 주 전략
1. CTR 낮은 포스트 → 제목/메타 설명 A/B 테스트 (위 개선 제안 참고)
2. 고성과 키워드 → 관련 심화 포스트 추가 작성
3. 순위 4~10위 쿼리 → 콘텐츠 보강으로 상위권 진입
4. 매핑된 포스트 글자수 3,000자 미만 → 보강 우선순위 높음
"""
    return md


# ── 메인 ─────────────────────────────────────────────────────────────────────

def run():
    print(f"[Analytics Agent] 주간 리포트 생성")

    today      = datetime.date.today()
    week_start = (today - datetime.timedelta(days=7)).isoformat()
    week_end   = today.isoformat()
    week_num   = today.isocalendar()[1]

    report_md = build_weekly_report(week_start, week_end)

    report_path = os.path.join(OUT_L, f"weekly_report_{today.year}-W{week_num:02d}.md")
    os.makedirs(OUT_L, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"\n[Analytics Agent] 완료 → {report_path}")
    return report_path


if __name__ == "__main__":
    run()
