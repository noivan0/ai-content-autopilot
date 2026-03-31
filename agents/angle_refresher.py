"""
Angle Refresher — P004
매주 실행: 81개 AI 도메인별 최신 세부 토픽 앵글을 다양한 소스에서 수집해 갱신
저장: output/angles/topic_angles_YYYY-WW.json

수집 소스:
  1. Google News RSS (도메인별 최신 뉴스 헤드라인)
  2. Reddit (r/artificial, r/MachineLearning, r/LocalLLaMA, r/ChatGPT 등)
  3. HackerNews (Algolia API)
  4. AI 공식 블로그 RSS
     - OpenAI: https://openai.com/blog/rss.xml
     - Anthropic: https://www.anthropic.com/rss.xml (없으면 news RSS)
     - Google DeepMind: https://deepmind.google/blog/rss.xml
     - Meta AI: https://ai.meta.com/blog/rss/
     - Mistral: https://mistral.ai/news/rss
     - DeepSeek: https://api.deepseek.com (없으면 gnews fallback)
     - HuggingFace: https://huggingface.co/blog/feed.xml
     - Stability AI: https://stability.ai/news/rss.xml (없으면 gnews)
  5. Brave Search (도메인 + "최신 2025" 쿼리)
"""

import os, json, datetime, time, urllib.request, urllib.parse, re, hashlib

BASE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(BASE, "output", "angles")
BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")

TODAY   = datetime.date.today().isoformat()
YEAR_WW = datetime.date.today().strftime("%Y-W%V")   # e.g. "2026-W14"

# ── 수집 대상 AI 공식 블로그 RSS ──────────────────────────────────────────────

OFFICIAL_BLOGS = [
    {"name": "OpenAI",         "domain": "ChatGPT OpenAI",            "rss": "https://openai.com/blog/rss.xml"},
    {"name": "Anthropic",      "domain": "Claude Anthropic",          "rss": "https://www.anthropic.com/rss.xml"},
    {"name": "Google DeepMind","domain": "Gemini Google AI",          "rss": "https://deepmind.google/blog/rss.xml"},
    {"name": "Meta AI",        "domain": "Llama Meta AI",             "rss": "https://ai.meta.com/blog/rss/"},
    {"name": "Mistral AI",     "domain": "Mistral AI",                "rss": "https://mistral.ai/news/rss"},
    {"name": "HuggingFace",    "domain": "HuggingFace 오픈소스",      "rss": "https://huggingface.co/blog/feed.xml"},
    {"name": "Microsoft AI",   "domain": "Copilot Microsoft AI",      "rss": "https://blogs.microsoft.com/ai/feed/"},
    {"name": "NVIDIA AI",      "domain": "AI 칩 반도체 NVIDIA",       "rss": "https://blogs.nvidia.com/feed/"},
    {"name": "AWS AI",         "domain": "AI API 통합",               "rss": "https://aws.amazon.com/blogs/machine-learning/feed/"},
    {"name": "Google AI Blog", "domain": "Gemini Google AI",          "rss": "https://blog.google/technology/ai/rss/"},
    {"name": "DeepSeek",       "domain": "DeepSeek AI 모델",          "rss": None},  # gnews fallback
    {"name": "Stability AI",   "domain": "Stable Diffusion 이미지생성","rss": None},  # gnews fallback
    {"name": "xAI",            "domain": "Grok xAI",                  "rss": None},  # gnews fallback
]

# ── Reddit 수집 대상 ──────────────────────────────────────────────────────────

REDDIT_SOURCES = [
    {"subreddit": "artificial",        "domain_hint": "AI 에이전트 자동화"},
    {"subreddit": "MachineLearning",   "domain_hint": "딥러닝 머신러닝"},
    {"subreddit": "LocalLLaMA",        "domain_hint": "양자화 GGUF llama.cpp"},
    {"subreddit": "ChatGPT",           "domain_hint": "ChatGPT OpenAI"},
    {"subreddit": "ClaudeAI",          "domain_hint": "Claude Anthropic"},
    {"subreddit": "GoogleGeminiAI",    "domain_hint": "Gemini Google AI"},
    {"subreddit": "StableDiffusion",   "domain_hint": "Stable Diffusion 이미지생성"},
    {"subreddit": "midjourney",        "domain_hint": "Midjourney AI 아트"},
    {"subreddit": "AIAssistants",      "domain_hint": "AI 생산성 활용"},
    {"subreddit": "OpenAI",            "domain_hint": "ChatGPT OpenAI"},
    {"subreddit": "LanguageModelNews", "domain_hint": "LLM 언어모델"},
    {"subreddit": "AIdev",             "domain_hint": "AI 코딩 개발"},
]

# 광고성 필터 키워드
AD_FILTER_WORDS = [
    "buy", "sale", "discount", "promo", "coupon", "offer", "deal",
    "구매", "할인", "특가", "이벤트", "프로모", "쿠폰", "혜택",
    "free shipping", "limited time", "click here",
]


# ── 수집 함수들 ───────────────────────────────────────────────────────────────

def fetch_rss(url: str, max_items: int = 10) -> list:
    """
    RSS/Atom 피드 파싱 — title, link, pubDate 반환. 실패 시 빈 리스트.
    - requests 없이 urllib 사용
    - XML에서 <title>, <link>, <pubDate> 또는 <updated> 추출
    - <![CDATA[...]]> 처리 포함
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 research-bot/1.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            xml = r.read().decode("utf-8", errors="replace")

        # CDATA 처리
        xml = re.sub(r"<!\[CDATA\[(.*?)\]\]>", lambda m: m.group(1), xml, flags=re.DOTALL)

        # item 또는 entry 태그 추출 (RSS 2.0 / Atom)
        items = re.findall(r"<(?:item|entry)>(.*?)</(?:item|entry)>", xml, re.DOTALL)
        results = []
        for item in items[:max_items]:
            title   = re.search(r"<title[^>]*>(.*?)</title>", item, re.DOTALL)
            link    = re.search(r"<link[^>]*>(.*?)</link>", item, re.DOTALL)
            pubdate = re.search(r"<(?:pubDate|updated|published)[^>]*>(.*?)</(?:pubDate|updated|published)>", item, re.DOTALL)

            t = re.sub(r"<[^>]+>", "", title.group(1)).strip() if title else ""
            l = re.sub(r"<[^>]+>", "", link.group(1)).strip()  if link  else ""
            p = re.sub(r"<[^>]+>", "", pubdate.group(1)).strip() if pubdate else ""

            if t:
                results.append({"title": t, "link": l, "pubDate": p})
        return results
    except Exception as e:
        print(f"  [RSS ERR] {url}: {e}")
        return []


def fetch_gnews(query: str, max_results: int = 8) -> list:
    """Google News RSS — 최근 1주일 뉴스"""
    try:
        q = urllib.parse.quote(f"{query} when:7d")
        url = f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            xml = r.read().decode("utf-8", errors="replace")

        # CDATA 처리
        xml = re.sub(r"<!\[CDATA\[(.*?)\]\]>", lambda m: m.group(1), xml, flags=re.DOTALL)

        items = re.findall(r"<item>(.*?)</item>", xml, re.DOTALL)
        results = []
        for item in items[:max_results]:
            title = re.search(r"<title>(.*?)</title>", item)
            link  = re.search(r"<link/>(.*?)<", item)
            pub   = re.search(r"<pubDate>(.*?)</pubDate>", item)
            t = re.sub(r"<[^>]+>", "", title.group(1)).strip() if title else ""
            if t:
                results.append({
                    "title":   t,
                    "url":     link.group(1).strip() if link else "",
                    "pubdate": pub.group(1).strip()  if pub  else "",
                })
        return results
    except Exception as e:
        print(f"  [GNews ERR] {e}")
        return []


def fetch_reddit_top(subreddit: str, limit: int = 10) -> list:
    """
    Reddit 해당 서브레딧 hot 포스트.
    User-Agent: research-bot/1.0
    반환: [{"title": ..., "score": ..., "url": ...}]
    """
    try:
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "research-bot/1.0",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read().decode("utf-8", errors="replace"))
        posts = data.get("data", {}).get("children", [])
        return [
            {
                "title": p["data"].get("title", ""),
                "score": p["data"].get("score", 0),
                "url":   p["data"].get("url", ""),
            }
            for p in posts if p.get("data", {}).get("title")
        ]
    except Exception as e:
        print(f"  [Reddit ERR] r/{subreddit}: {e}")
        return []


def fetch_hn_trending(query: str, max_results: int = 8) -> list:
    """
    HackerNews Algolia — points>5 스토리
    URL: https://hn.algolia.com/api/v1/search?query={query}&tags=story&numericFilters=points>5&hitsPerPage={max_results}
    """
    try:
        encoded_query = urllib.parse.quote(query)
        url = (
            f"https://hn.algolia.com/api/v1/search"
            f"?query={encoded_query}&tags=story"
            f"&numericFilters=points>5&hitsPerPage={max_results}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 research-bot/1.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read().decode("utf-8", errors="replace"))
        hits = data.get("hits", [])
        return [
            {
                "title":  h.get("title", ""),
                "url":    h.get("url", ""),
                "points": h.get("points", 0),
            }
            for h in hits if h.get("title")
        ]
    except Exception as e:
        print(f"  [HN ERR] {e}")
        return []


def fetch_brave(query: str, count: int = 10) -> list:
    """Brave Search"""
    if not BRAVE_API_KEY:
        return []
    try:
        url = (
            f"https://api.search.brave.com/res/v1/web/search"
            f"?q={urllib.parse.quote(query)}&count={count}&search_lang=ko&freshness=pw"
        )
        req = urllib.request.Request(url, headers={
            "Accept": "application/json",
            "X-Subscription-Token": BRAVE_API_KEY,
        })
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read().decode("utf-8", errors="replace"))
        results = data.get("web", {}).get("results", [])
        return [
            {
                "title":   r.get("title", ""),
                "url":     r.get("url", ""),
                "snippet": r.get("description", ""),
            }
            for r in results
        ]
    except Exception as e:
        print(f"  [Brave ERR] {e}")
        return []


def extract_angle(title: str, domain: str) -> str | None:
    """
    뉴스/포스트 제목에서 블로그 앵글(세부 주제)을 추출.
    - 언론사 이름 제거 (- 이후, | 이후)
    - 80자 이하로 정리
    - 너무 짧으면 (10자 미만) None 반환
    - 광고성 문구 필터 (Buy, Sale, Discount, 구매, 할인 등)
    """
    if not title:
        return None

    # 언론사 이름 제거 (파이프 또는 하이픈 이후)
    cleaned = re.sub(r"\s*\|.*$", "", title).strip()
    cleaned = re.sub(r"\s*-\s*[^-]{3,40}$", "", cleaned).strip()

    # HTML 태그 제거
    cleaned = re.sub(r"<[^>]+>", "", cleaned).strip()

    # 80자 이하로 자르기
    if len(cleaned) > 80:
        cleaned = cleaned[:80].rsplit(" ", 1)[0].strip()

    # 너무 짧으면 None
    if len(cleaned) < 10:
        return None

    # 광고성 문구 필터
    lower = cleaned.lower()
    for ad_word in AD_FILTER_WORDS:
        if ad_word in lower:
            return None

    return cleaned


def collect_angles_for_domain(domain: str, existing_angles: set) -> list:
    """
    하나의 도메인에 대해 모든 소스에서 앵글 수집.
    - existing_angles: 이미 있는 앵글 (중복 제외용)
    - 반환: 새 앵글 문자열 리스트 (최대 20개, 중복 제거)
    """
    angles = []

    # 1. GNews
    news = fetch_gnews(domain, max_results=8)
    for n in news:
        angle = extract_angle(n["title"], domain)
        if angle and angle not in existing_angles:
            angles.append(angle)

    # 2. Brave Search
    web = fetch_brave(f"{domain} 최신 소식 2025", count=8)
    for w in web:
        angle = extract_angle(w.get("title", ""), domain)
        if angle and angle not in existing_angles:
            angles.append(angle)

    # 3. HackerNews
    hn = fetch_hn_trending(domain, max_results=8)
    for h in hn:
        angle = extract_angle(h.get("title", ""), domain)
        if angle and angle not in existing_angles:
            angles.append(angle)

    # 4. Reddit (domain_hint로 매칭되는 서브레딧)
    for src in REDDIT_SOURCES:
        if src["domain_hint"] in domain or domain in src["domain_hint"]:
            posts = fetch_reddit_top(src["subreddit"], limit=8)
            for p in posts:
                angle = extract_angle(p.get("title", ""), domain)
                if angle and angle not in existing_angles:
                    angles.append(angle)

    # 중복 제거 후 최대 20개
    seen   = set()
    result = []
    for a in angles:
        if a not in seen and a not in existing_angles:
            seen.add(a)
            result.append(a)
        if len(result) >= 20:
            break
    return result


def collect_official_blog_angles() -> dict:
    """
    공식 블로그 RSS에서 도메인별 앵글 수집.
    반환: {domain: [angle, ...]}
    """
    result = {}
    for blog in OFFICIAL_BLOGS:
        domain = blog["domain"]
        angles = []
        if blog["rss"]:
            items = fetch_rss(blog["rss"], max_items=10)
            for item in items:
                angle = extract_angle(item.get("title", ""), domain)
                if angle:
                    angles.append(angle)
        else:
            # gnews fallback
            news = fetch_gnews(blog["name"], max_results=8)
            for n in news:
                angle = extract_angle(n["title"], domain)
                if angle:
                    angles.append(angle)
        if angles:
            result[domain] = result.get(domain, []) + angles
        time.sleep(0.5)
    return result


def run():
    """
    전체 실행:
    1. 이전 주간 파일 로드 (기존 앵글 파악)
    2. 도메인별 신규 앵글 수집
    3. 기존 + 신규 병합 (신규를 앞에, 최대 50개/도메인)
    4. output/angles/topic_angles_YYYY-WW.json 저장
    """
    import sys
    os.makedirs(OUTPUT, exist_ok=True)
    out_path = os.path.join(OUTPUT, f"topic_angles_{YEAR_WW}.json")

    # 이미 이번 주 파일 있으면 스킵 (강제 갱신: --force 옵션)
    force = "--force" in sys.argv
    if os.path.exists(out_path) and not force:
        print(f"[AngleRefresher] 이번 주 파일 이미 존재: {out_path}")
        print("  강제 갱신: python3 -m agents.angle_refresher --force")
        return json.load(open(out_path, encoding="utf-8"))

    print(f"[AngleRefresher] {YEAR_WW} 앵글 갱신 시작")

    # 이전 주 파일에서 기존 앵글 로드
    prev_date = datetime.date.today() - datetime.timedelta(days=7)
    prev_ww   = prev_date.strftime("%Y-W%V")
    prev_path = os.path.join(OUTPUT, f"topic_angles_{prev_ww}.json")
    existing  = {}
    if os.path.exists(prev_path):
        existing = json.load(open(prev_path, encoding="utf-8")).get("angles", {})
        print(f"  이전 주 파일 로드: {prev_path} ({len(existing)}개 도메인)")

    # 공식 블로그 앵글 수집
    print("\n[1/3] 공식 블로그 RSS 수집 중...")
    blog_angles = collect_official_blog_angles()

    # 도메인별 앵글 수집 (AI_DOMAINS 전체)
    from agents.research import AI_DOMAINS, TOPIC_SUBTYPES
    print(f"\n[2/3] 전체 {len(AI_DOMAINS)}개 도메인 앵글 수집 중...")
    fresh_angles = {}
    for i, domain in enumerate(AI_DOMAINS, 1):
        print(f"  [{i:2d}/{len(AI_DOMAINS)}] {domain[:40]}")
        existing_set = set(existing.get(domain, []))
        new_angles   = collect_angles_for_domain(domain, existing_set)
        # 공식 블로그 앵글 병합
        blog = blog_angles.get(domain, [])
        new_angles = blog + new_angles
        # 중복 제거
        seen    = set()
        deduped = []
        for a in new_angles:
            if a not in seen and a not in existing_set:
                seen.add(a)
                deduped.append(a)
        fresh_angles[domain] = deduped
        time.sleep(0.5)

    # 병합: 신규(fresh) + 기존(existing) + 정적 fallback
    print("\n[3/3] 병합 및 저장 중...")
    merged = {}
    for domain in AI_DOMAINS:
        fresh  = fresh_angles.get(domain, [])
        old    = existing.get(domain, [])
        static = TOPIC_SUBTYPES.get(domain, [])
        # 신규 앵글 앞에, 기존 뒤에, 중복 제거, 최대 50개
        combined = []
        seen     = set()
        for a in fresh + old + static:
            if a and a not in seen:
                seen.add(a)
                combined.append(a)
            if len(combined) >= 50:
                break
        merged[domain] = combined

    result = {
        "week":          YEAR_WW,
        "generated":     datetime.datetime.utcnow().isoformat(),
        "sources":       ["gnews", "brave", "hackernews", "reddit", "official_blogs"],
        "domain_count":  len(merged),
        "total_angles":  sum(len(v) for v in merged.values()),
        "angles":        merged,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n[AngleRefresher] 완료 → {out_path}")
    print(f"  도메인: {result['domain_count']}개")
    print(f"  총 앵글: {result['total_angles']}개")
    return result


if __name__ == "__main__":
    run()
