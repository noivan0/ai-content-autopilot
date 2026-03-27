"""
Research Agent — P004
매일 최신 AI 트렌드 기반으로 주제 3개 발굴 + 자료 수집
- 고정 키워드 없음: 매일 구글 뉴스 트렌드로 실시간 후보 생성
- 과거 포스팅 이력 비교해 중복 주제 자동 제외
"""
import os, json, datetime, time, urllib.request, urllib.parse, re

BASE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(BASE, "output", "topics")
POSTS  = os.path.join(BASE, "output", "posts")

BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")
TODAY = datetime.date.today().isoformat()

# AI 도메인 카테고리 (매일 뉴스 트렌드로 구체 키워드 동적 생성)
AI_DOMAINS = [
    "ChatGPT OpenAI",
    "Claude Anthropic",
    "Gemini Google AI",
    "Manus AI 에이전트",
    "LLM 언어모델",
    "AI 에이전트 자동화",
    "멀티모달 AI",
    "AI 코딩 개발",
    "프롬프트 엔지니어링",
    "AI 논문 연구",
    "딥러닝 머신러닝",
    "AI 생산성 활용",
    "RAG 벡터DB",
    "오픈소스 AI 모델",
    "AI 규제 정책",
]


# ── 유틸 ─────────────────────────────────────────────────────────────────────

def http_get(url, headers=None, timeout=12):
    h = {"User-Agent": "Mozilla/5.0 Chrome/120", "Accept": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def brave_search(query, count=10):
    if not BRAVE_API_KEY:
        return []
    url = (f"https://api.search.brave.com/res/v1/web/search"
           f"?q={urllib.parse.quote(query)}&count={count}&search_lang=ko&freshness=pw")
    try:
        data = http_get(url, headers={
            "Accept": "application/json",
            "X-Subscription-Token": BRAVE_API_KEY
        })
        results = data.get("web", {}).get("results", [])
        return [{"title": r.get("title",""), "url": r.get("url",""),
                 "snippet": r.get("description","")} for r in results]
    except Exception as e:
        print(f"  [Brave ERR] {e}")
        return []


def fetch_gnews(query, max_results=5):
    """Google News RSS — 최근 1주일 뉴스"""
    try:
        q = urllib.parse.quote(f"{query} when:7d")
        url = f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            xml = r.read().decode("utf-8", errors="replace")
        items = re.findall(r"<item>(.*?)</item>", xml, re.DOTALL)
        results = []
        for item in items[:max_results]:
            title = re.search(r"<title>(.*?)</title>", item)
            link  = re.search(r"<link/>(.*?)<", item)
            pub   = re.search(r"<pubDate>(.*?)</pubDate>", item)
            results.append({
                "title":   re.sub(r"<[^>]+>", "", title.group(1)).strip() if title else "",
                "url":     link.group(1).strip() if link else "",
                "pubdate": pub.group(1).strip()  if pub  else "",
            })
        return [r for r in results if r["title"]]
    except Exception as e:
        print(f"  [GNews ERR] {e}")
        return []


def fetch_arxiv(query, max_results=3):
    try:
        q = urllib.parse.quote(query)
        url = (f"https://export.arxiv.org/api/query"
               f"?search_query=all:{q}&sortBy=submittedDate&sortOrder=descending&max_results={max_results}")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            xml = r.read().decode("utf-8", errors="replace")
        entries = re.findall(r"<entry>(.*?)</entry>", xml, re.DOTALL)
        results = []
        for e in entries:
            title   = re.search(r"<title>(.*?)</title>", e, re.DOTALL)
            summary = re.search(r"<summary>(.*?)</summary>", e, re.DOTALL)
            link    = re.search(r'href="(https://arxiv\.org/abs/[^"]+)"', e)
            results.append({
                "title":   title.group(1).strip().replace("\n", " ") if title else "",
                "summary": summary.group(1).strip().replace("\n", " ")[:300] if summary else "",
                "url":     link.group(1) if link else "",
            })
        return [r for r in results if r["title"]]
    except Exception as e:
        print(f"  [arXiv ERR] {e}")
        return []


def fetch_github_trending():
    try:
        url = ("https://api.github.com/search/repositories"
               "?q=topic:llm+topic:ai+pushed:>2025-01-01&sort=stars&order=desc&per_page=5")
        data = http_get(url, headers={"Accept": "application/vnd.github+json"})
        repos = data.get("items", [])
        return [{"name": r.get("full_name",""), "desc": r.get("description",""),
                 "stars": r.get("stargazers_count", 0), "url": r.get("html_url","")} for r in repos]
    except Exception as e:
        print(f"  [GitHub ERR] {e}")
        return []


# ── 중복 방지 ─────────────────────────────────────────────────────────────────

def load_posted_history(days=60) -> set:
    """최근 N일 포스팅된 키워드/제목 집합 로드"""
    used = set()
    cutoff = datetime.date.today() - datetime.timedelta(days=days)

    # output/posts/ 의 메타 파일 스캔
    if not os.path.exists(POSTS):
        return used

    for fname in os.listdir(POSTS):
        if not fname.endswith("_meta.json"):
            continue
        try:
            # 파일명에서 날짜 추출 (post_YYYY-MM-DD_N_meta.json)
            parts = fname.split("_")
            if len(parts) < 3:
                continue
            fdate = datetime.date.fromisoformat(parts[1] + "-" + parts[2] + "-" + parts[3])
            if fdate < cutoff:
                continue
        except Exception:
            pass

        try:
            meta = json.load(open(os.path.join(POSTS, fname), encoding="utf-8"))
            title   = meta.get("title", "").lower()
            keyword = meta.get("primary_keyword", "").lower()
            topic   = meta.get("topic", "").lower()
            used.add(title)
            used.add(keyword)
            used.add(topic)
        except Exception:
            pass

    # output/topics/ 의 daily_topics 스캔
    if os.path.exists(OUTPUT):
        for fname in os.listdir(OUTPUT):
            if not fname.startswith("daily_topics_") or not fname.endswith(".json"):
                continue
            try:
                date_str = fname.replace("daily_topics_", "").replace(".json", "")
                fdate    = datetime.date.fromisoformat(date_str)
                if fdate < cutoff or fdate.isoformat() == TODAY:
                    continue
                data = json.load(open(os.path.join(OUTPUT, fname), encoding="utf-8"))
                for t in data.get("topics", []):
                    used.add(t.get("query", "").lower())
                    used.add(t.get("final_title", "").lower())
            except Exception:
                pass

    print(f"  [중복방지] 최근 {days}일 포스팅 이력 {len(used)}개 로드")
    return used


def similarity_score(a: str, b: str) -> float:
    """단어 기반 유사도 (0~1)"""
    words_a = set(re.findall(r"[\w가-힣]+", a.lower()))
    words_b = set(re.findall(r"[\w가-힣]+", b.lower()))
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union        = words_a | words_b
    return len(intersection) / len(union)


def is_duplicate(candidate: str, history: set, threshold=0.5) -> bool:
    """후보 주제가 기존 이력과 유사한지 검사"""
    for h in history:
        if not h:
            continue
        if similarity_score(candidate, h) >= threshold:
            return True
    return False


# ── 실시간 트렌드 기반 키워드 생성 ───────────────────────────────────────────

def generate_trending_queries() -> list:
    """
    AI 도메인별 최신 뉴스를 수집해 실제 트렌딩 헤드라인 기반 쿼리 생성
    고정 키워드 대신 오늘의 뉴스에서 동적으로 추출
    """
    queries = []
    print("  [트렌드 수집] 도메인별 최신 뉴스 기반 쿼리 생성...")

    for domain in AI_DOMAINS:
        news = fetch_gnews(domain, max_results=3)
        if news:
            # 뉴스 제목에서 핵심 키워드 추출해 검색 쿼리로 변환
            for n in news[:2]:
                title = n.get("title", "")
                # 언론사 이름 제거 (- 이후)
                title = re.sub(r"\s*-\s*[^-]+$", "", title).strip()
                if len(title) > 10:
                    queries.append({
                        "query":   title[:80],
                        "domain":  domain,
                        "source":  "gnews",
                        "pubdate": n.get("pubdate", ""),
                    })
        # 도메인 자체도 후보로 추가
        queries.append({"query": domain, "domain": domain, "source": "seed", "pubdate": ""})
        time.sleep(0.3)

    print(f"  [트렌드 수집] {len(queries)}개 쿼리 후보 생성")
    return queries


def score_candidate(cand: dict, history: set) -> dict:
    """
    후보 쿼리 점수 산출
    - 최신 뉴스 건수 (x3) + 웹 결과 풍부도 + 논문 존재 여부
    - 중복 시 점수 0 처리
    """
    query = cand["query"]

    # 중복 검사
    if is_duplicate(query, history):
        return {**cand, "score": -1, "duplicate": True, "news": [], "web": [], "papers": []}

    news   = fetch_gnews(query, max_results=5)
    web    = brave_search(query, count=5)
    papers = fetch_arxiv(re.sub(r"[^\w\s가-힣]", "", query)[:50], max_results=2)

    # 뉴스 신선도: 오늘/어제 뉴스는 가중치 높게
    fresh_news = 0
    for n in news:
        pd = n.get("pubdate", "")
        if pd and any(x in pd for x in ["today", TODAY, str(datetime.date.today() - datetime.timedelta(1))]):
            fresh_news += 2
        else:
            fresh_news += 1

    news_score   = fresh_news
    web_score    = len(web)
    paper_score  = len(papers) * 2
    source_bonus = 3 if cand.get("source") == "gnews" else 0  # 뉴스 기반이면 가산점

    total = news_score * 3 + web_score + paper_score + source_bonus

    time.sleep(0.4)
    return {
        **cand,
        "score":      total,
        "duplicate":  False,
        "news":       news,
        "web":        web,
        "papers":     papers,
        "news_score": news_score,
        "web_score":  web_score,
    }


def select_top_topics(n=3) -> list:
    """중복 없는 상위 n개 주제 선정"""
    history = load_posted_history(days=60)

    # 오늘 트렌딩 쿼리 생성
    candidates_raw = generate_trending_queries()

    # 도메인 다양성 확보: 같은 도메인에서 2개 이상 안 뽑음
    domain_seen = {}
    deduped = []
    for c in candidates_raw:
        d = c.get("domain", "")
        if domain_seen.get(d, 0) < 2:
            deduped.append(c)
            domain_seen[d] = domain_seen.get(d, 0) + 1

    print(f"\n  [점수 산출] {len(deduped)}개 후보 평가 중...")
    scored = []
    for cand in deduped:
        result = score_candidate(cand, history)
        if result["score"] > 0:
            scored.append(result)
            print(f"    [{result['score']:3d}점] {result['query'][:60]}")
        else:
            if result.get("duplicate"):
                print(f"    [중복제외] {result['query'][:60]}")

    # 점수 내림차순 정렬 → 도메인 다양성 고려해 최종 n개 선정
    scored.sort(key=lambda x: -x["score"])

    # 최종 선정: 도메인 중복 방지
    selected = []
    used_domains = set()
    for s in scored:
        d = s.get("domain", "")
        if d not in used_domains:
            selected.append(s)
            used_domains.add(d)
        if len(selected) >= n:
            break

    # 부족하면 도메인 중복 허용해서 채우기
    if len(selected) < n:
        for s in scored:
            if s not in selected:
                selected.append(s)
            if len(selected) >= n:
                break

    print(f"\n  [최종 선정] {len(selected)}개:")
    for i, t in enumerate(selected, 1):
        print(f"    {i}. [{t['score']}점] [{t['domain']}] {t['query'][:60]}")

    return selected[:n]


def build_topic_package(topic_data: dict) -> dict:
    query = topic_data["query"]
    print(f"  [상세 수집] {query[:60]}")

    extra_web    = brave_search(f"{query} 완벽 가이드 2025", count=8)
    extra_papers = fetch_arxiv(query[:50], max_results=3)
    github       = fetch_github_trending()

    return {
        "query":        query,
        "domain":       topic_data.get("domain", ""),
        "source":       topic_data.get("source", ""),
        "score":        topic_data["score"],
        "news":         topic_data.get("news", []),
        "web":          topic_data.get("web", []) + extra_web,
        "papers":       topic_data.get("papers", []) + extra_papers,
        "github":       github,
        "collected_at": datetime.datetime.utcnow().isoformat(),
    }


# ── 메인 ─────────────────────────────────────────────────────────────────────

def run():
    print(f"[Research Agent] {TODAY} 시작")

    output_path = os.path.join(OUTPUT, f"daily_topics_{TODAY}.json")
    if os.path.exists(output_path):
        print(f"  이미 수집된 파일 존재: {output_path}")
        return json.load(open(output_path))

    print("\n[1/2] 트렌드 기반 주제 선정 중...")
    top_topics = select_top_topics(n=3)

    if not top_topics:
        raise RuntimeError("선정된 주제가 없습니다. API 키 또는 네트워크 확인 필요")

    print("\n[2/2] 상세 자료 수집 중...")
    packages = []
    for t in top_topics:
        pkg = build_topic_package(t)
        packages.append(pkg)
        time.sleep(1)

    result = {"date": TODAY, "topics": packages}

    os.makedirs(OUTPUT, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n[Research Agent] 완료 → {output_path}")
    return result


if __name__ == "__main__":
    run()
