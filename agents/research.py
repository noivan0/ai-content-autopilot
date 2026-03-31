"""
Research Agent — P004 (개선판 v2)
매일 최신 AI 트렌드 기반으로 주제 3개 발굴 + 자료 수집

개선 사항:
- 중복방지 강화: 임계값 0.35 + bigram + 핵심 단어 3개 이상 겹치면 무조건 중복
- AI 도메인 60+개로 확장
- 날짜 seed 기반 도메인 로테이션 시스템 (매일 20개 선택, 전체 순환)
- 신규 채널: HackerNews, Reddit, ProductHunt, arXiv 주간
- 포지셔닝 다양화: 뉴스성 / 기술심층 / 산업분석 / 실용가이드 / 트렌드분석 / 국내이슈
- 이력 DB 통합: p004-blogger/posts/*.md frontmatter + output/published/*.json
"""
import os, json, datetime, time, urllib.request, urllib.parse, re, hashlib
import xml.etree.ElementTree as ET

BASE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(BASE, "output", "topics")
POSTS  = os.path.join(BASE, "output", "posts")

BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")
TODAY = datetime.date.today().isoformat()

# ── AI 도메인 카테고리 (60+개) ─────────────────────────────────────────────

AI_DOMAINS = [
    # 기존 15개
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

    # AI 모델/서비스
    "Grok xAI",
    "Llama Meta AI",
    "Mistral AI",
    "Perplexity AI",
    "Copilot Microsoft AI",
    "DeepSeek AI 모델",
    "Qwen Alibaba AI",
    "Phi Microsoft 소형LLM",
    "Command R Cohere",
    "Stable Diffusion 이미지생성",
    "Midjourney AI 아트",
    "DALL-E OpenAI 이미지",
    "Runway Gen AI 영상",
    "Sora OpenAI 영상생성",
    "ElevenLabs AI 음성",
    "Whisper 음성인식",
    "HuggingFace 오픈소스",

    # AI 응용/산업
    "AI 헬스케어 의료",
    "AI 교육 에듀테크",
    "AI 법률 리걸테크",
    "AI 금융 핀테크",
    "AI 부동산",
    "AI 마케팅 광고",
    "AI 게임 개발",
    "AI 음악 작곡",
    "AI 영상편집",
    "AI 번역 언어",
    "AI 검색엔진",
    "AI 사이버보안",
    "AI 로보틱스 자율주행",
    "AI 제조 스마트팩토리",
    "AI 농업 푸드테크",

    # AI 기술/개념
    "파인튜닝 LoRA PEFT",
    "양자화 GGUF llama.cpp",
    "컨텍스트 윈도우 LLM",
    "AI 할루시네이션 해결",
    "Mixture of Experts MoE",
    "AI 멀티에이전트 시스템",
    "컴퓨터 비전 YOLO",
    "강화학습 RLHF",
    "AI 워크플로우 n8n",
    "벡터 데이터베이스 Pinecone Chroma",
    "LangChain LlamaIndex",
    "AI API 통합",
    "엣지 AI 온디바이스",
    "AI 칩 반도체 NVIDIA",
    "Transformer 아키텍처",

    # AI 트렌드/비즈니스
    "AI 스타트업 투자",
    "AI 일자리 취업",
    "AI 윤리 편향",
    "AI 저작권 지적재산",
    "AI 규제 EU AI Act",
    "AI 데이터센터 전력",
    "오픈소스 vs 클로즈드 AI",
    "AI 구독 서비스 비교",
    "AI 생산성 측정",
    "AI PC 노트북 추천",
    "AI 스마트폰 온디바이스",
    "AI 웨어러블",

    # 한국/글로벌 AI
    "한국 AI 정책 NIPA",
    "네이버 CLOVA AI",
    "카카오 AI",
    "삼성 AI",
    "SK AI 투자",
    "KT AI",
    "국내 AI 스타트업",
]

DAILY_DOMAINS_COUNT = 20

# ── 포지셔닝 매핑 ──────────────────────────────────────────────────────────

DOMAIN_POSITIONING = {
    # 뉴스성
    "ChatGPT OpenAI":          "뉴스성",
    "Claude Anthropic":        "뉴스성",
    "Gemini Google AI":        "뉴스성",
    "Grok xAI":                "뉴스성",
    "DeepSeek AI 모델":        "뉴스성",
    "Sora OpenAI 영상생성":    "뉴스성",
    "Manus AI 에이전트":       "뉴스성",
    "Perplexity AI":           "뉴스성",
    "Copilot Microsoft AI":    "뉴스성",
    "Llama Meta AI":           "뉴스성",
    "Mistral AI":              "뉴스성",
    "Qwen Alibaba AI":         "뉴스성",

    # 기술심층
    "LLM 언어모델":                    "기술심층",
    "멀티모달 AI":                      "기술심층",
    "AI 코딩 개발":                     "기술심층",
    "프롬프트 엔지니어링":              "기술심층",
    "AI 논문 연구":                     "기술심층",
    "딥러닝 머신러닝":                  "기술심층",
    "RAG 벡터DB":                       "기술심층",
    "파인튜닝 LoRA PEFT":               "기술심층",
    "양자화 GGUF llama.cpp":            "기술심층",
    "컨텍스트 윈도우 LLM":             "기술심층",
    "AI 할루시네이션 해결":             "기술심층",
    "Mixture of Experts MoE":           "기술심층",
    "AI 멀티에이전트 시스템":           "기술심층",
    "컴퓨터 비전 YOLO":                 "기술심층",
    "강화학습 RLHF":                    "기술심층",
    "벡터 데이터베이스 Pinecone Chroma": "기술심층",
    "LangChain LlamaIndex":             "기술심층",
    "Transformer 아키텍처":             "기술심층",
    "HuggingFace 오픈소스":             "기술심층",
    "Phi Microsoft 소형LLM":            "기술심층",
    "Command R Cohere":                 "기술심층",
    "Whisper 음성인식":                 "기술심층",
    "ElevenLabs AI 음성":               "기술심층",
    "Stable Diffusion 이미지생성":      "기술심층",
    "Midjourney AI 아트":               "기술심층",
    "DALL-E OpenAI 이미지":             "기술심층",
    "Runway Gen AI 영상":               "기술심층",
    "AI 칩 반도체 NVIDIA":              "기술심층",
    "엣지 AI 온디바이스":               "기술심층",

    # 산업분석
    "AI 헬스케어 의료":     "산업분석",
    "AI 교육 에듀테크":     "산업분석",
    "AI 법률 리걸테크":     "산업분석",
    "AI 금융 핀테크":       "산업분석",
    "AI 부동산":            "산업분석",
    "AI 마케팅 광고":       "산업분석",
    "AI 게임 개발":         "산업분석",
    "AI 음악 작곡":         "산업분석",
    "AI 영상편집":          "산업분석",
    "AI 번역 언어":         "산업분석",
    "AI 검색엔진":          "산업분석",
    "AI 사이버보안":        "산업분석",
    "AI 로보틱스 자율주행": "산업분석",
    "AI 제조 스마트팩토리": "산업분석",
    "AI 농업 푸드테크":     "산업분석",

    # 실용가이드
    "AI 에이전트 자동화":  "실용가이드",
    "AI 생산성 활용":      "실용가이드",
    "AI 워크플로우 n8n":   "실용가이드",
    "AI API 통합":         "실용가이드",
    "AI PC 노트북 추천":   "실용가이드",
    "AI 스마트폰 온디바이스": "실용가이드",
    "AI 웨어러블":         "실용가이드",
    "AI 구독 서비스 비교": "실용가이드",

    # 트렌드분석
    "AI 스타트업 투자":      "트렌드분석",
    "AI 일자리 취업":        "트렌드분석",
    "AI 윤리 편향":          "트렌드분석",
    "AI 저작권 지적재산":    "트렌드분석",
    "AI 규제 EU AI Act":     "트렌드분석",
    "AI 데이터센터 전력":    "트렌드분석",
    "오픈소스 vs 클로즈드 AI": "트렌드분석",
    "AI 생산성 측정":        "트렌드분석",
    "AI 규제 정책":          "트렌드분석",
    "오픈소스 AI 모델":      "트렌드분석",

    # 국내이슈
    "한국 AI 정책 NIPA": "국내이슈",
    "네이버 CLOVA AI":   "국내이슈",
    "카카오 AI":         "국내이슈",
    "삼성 AI":           "국내이슈",
    "SK AI 투자":        "국내이슈",
    "KT AI":             "국내이슈",
    "국내 AI 스타트업":  "국내이슈",
}

CONTENT_ANGLES = {
    "뉴스성":   "오늘 일어난 일 → 의미 → 독자 영향 분석",
    "기술심층": "개념 설명 → 작동 원리 → 실습 예시 → 한계와 대안",
    "산업분석": "현황 파악 → 주요 플레이어 → 시장 전망 → 독자 기회",
    "실용가이드": "왜 써야 하나 → 단계별 방법 → 실전 팁 → 주의사항",
    "트렌드분석": "트렌드 배경 → 데이터 근거 → 시사점 → 미래 예측",
    "국내이슈":  "국내 배경 → 현황 → 해외 비교 → 시사점과 전망",
}


# ── 도메인 로테이션 ────────────────────────────────────────────────────────

def get_todays_domains() -> list:
    """날짜 seed 기반 20개 도메인 선택 — 전체 순환 보장"""
    seed = int(hashlib.md5(TODAY.encode()).hexdigest(), 16) % len(AI_DOMAINS)
    rotated = AI_DOMAINS[seed:] + AI_DOMAINS[:seed]
    return rotated[:DAILY_DOMAINS_COUNT]


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


def fetch_arxiv_weekly() -> list:
    """arXiv 최신 AI/ML/NLP 논문 10편 → 쿼리 후보 리스트"""
    try:
        url = ("https://export.arxiv.org/api/query"
               "?search_query=cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.CL"
               "&sortBy=submittedDate&sortOrder=descending&max_results=10")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            xml = r.read().decode("utf-8", errors="replace")
        entries = re.findall(r"<entry>(.*?)</entry>", xml, re.DOTALL)
        results = []
        for e in entries:
            title = re.search(r"<title>(.*?)</title>", e, re.DOTALL)
            if title:
                t = title.group(1).strip().replace("\n", " ")
                results.append({
                    "query":   t[:80],
                    "domain":  "AI 논문 연구",
                    "source":  "arxiv_weekly",
                    "pubdate": "",
                })
        return results
    except Exception as e:
        print(f"  [arXiv Weekly ERR] {e}")
        return []


def fetch_hackernews(query, max_results=5) -> list:
    """HackerNews Algolia API — 포인트 10 이상 스토리"""
    try:
        encoded_query = urllib.parse.quote(query)
        url = (f"https://hn.algolia.com/api/v1/search"
               f"?query={encoded_query}&tags=story"
               f"&numericFilters=points>10&hitsPerPage={max_results}")
        data = http_get(url)
        hits = data.get("hits", [])
        return [{
            "title":        h.get("title", ""),
            "url":          h.get("url", ""),
            "points":       h.get("points", 0),
            "num_comments": h.get("num_comments", 0),
        } for h in hits if h.get("title")]
    except Exception as e:
        print(f"  [HN ERR] {e}")
        return []


def fetch_reddit_ai(query, max_results=5) -> list:
    """Reddit AI 관련 서브레딧 검색"""
    try:
        encoded_query = urllib.parse.quote(query)
        url = (f"https://www.reddit.com/r/artificial+MachineLearning+LocalLLaMA"
               f"/search.json?q={encoded_query}&sort=hot&limit={max_results}&restrict_sr=1")
        req = urllib.request.Request(url, headers={
            "User-Agent": "research-bot/1.0",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read().decode("utf-8", errors="replace"))
        posts = data.get("data", {}).get("children", [])
        return [{
            "title":     p["data"].get("title", ""),
            "url":       p["data"].get("url", ""),
            "score":     p["data"].get("score", 0),
            "subreddit": p["data"].get("subreddit", ""),
        } for p in posts if p.get("data", {}).get("title")]
    except Exception as e:
        print(f"  [Reddit ERR] {e}")
        return []


def fetch_producthunt_ai(max_results=5) -> list:
    """Product Hunt RSS에서 AI 관련 제품 필터"""
    try:
        url = "https://www.producthunt.com/feed"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            xml_bytes = r.read()

        # XML 파싱
        try:
            root = ET.fromstring(xml_bytes.decode("utf-8", errors="replace"))
        except ET.ParseError:
            return []

        items = root.findall(".//item")
        results = []
        for item in items:
            title_el = item.find("title")
            link_el  = item.find("link")
            desc_el  = item.find("description")

            title   = title_el.text.strip() if title_el is not None and title_el.text else ""
            link    = link_el.text.strip()  if link_el  is not None and link_el.text  else ""
            tagline = desc_el.text.strip()  if desc_el  is not None and desc_el.text  else ""

            # AI / GPT / LLM 포함 항목만
            combined = (title + " " + tagline).upper()
            if any(kw in combined for kw in ["AI", "GPT", "LLM"]):
                results.append({"name": title, "url": link, "tagline": tagline})

            if len(results) >= max_results:
                break

        return results
    except Exception as e:
        print(f"  [ProductHunt ERR] {e}")
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

# 중복 판정 시 핵심 키워드 (3개 이상 겹치면 무조건 중복)
CORE_KEYWORDS = {
    "claude", "chatgpt", "gemini", "gpt", "gpt-4", "gpt-5",
    "ai안전", "ai규제", "openai", "anthropic", "google",
    "llama", "mistral", "deepseek", "perplexity", "copilot",
    "midjourney", "stablediffusion", "sora", "runway",
    "langchain", "llamaindex", "huggingface",
    "transformer", "rlhf", "lora", "gguf",
}


def get_words(text: str) -> set:
    """텍스트에서 단어 집합 추출"""
    return set(re.findall(r"[\w가-힣]+", text.lower()))


def get_bigrams(text: str) -> set:
    """텍스트에서 2-gram 집합 추출"""
    words = re.findall(r"[\w가-힣]+", text.lower())
    if len(words) < 2:
        return set()
    return {(words[i], words[i+1]) for i in range(len(words)-1)}


def similarity_score(a: str, b: str) -> float:
    """단어 기반 + bigram 기반 유사도 (0~1), 두 값의 평균"""
    words_a = get_words(a)
    words_b = get_words(b)
    bigrams_a = get_bigrams(a)
    bigrams_b = get_bigrams(b)

    # 단어 유사도
    if words_a and words_b:
        word_sim = len(words_a & words_b) / len(words_a | words_b)
    else:
        word_sim = 0.0

    # bigram 유사도
    if bigrams_a and bigrams_b:
        bigram_sim = len(bigrams_a & bigrams_b) / len(bigrams_a | bigrams_b)
    else:
        bigram_sim = 0.0

    # 평균
    return (word_sim + bigram_sim) / 2.0


def has_core_keyword_overlap(a: str, b: str, threshold=3) -> bool:
    """핵심 단어가 threshold개 이상 겹치면 True"""
    words_a = get_words(a) & CORE_KEYWORDS
    words_b = get_words(b) & CORE_KEYWORDS
    return len(words_a & words_b) >= threshold


def is_duplicate(candidate: str, history: set, threshold=0.35) -> bool:
    """
    후보 주제가 기존 이력과 유사한지 검사
    - 임계값 0.35 (강화)
    - bigram 포함 유사도
    - 핵심 단어 3개 이상 겹치면 무조건 중복
    """
    cand_lower = candidate.lower()
    for h in history:
        if not h:
            continue
        h_lower = h.lower()
        # 핵심 키워드 3개 이상 겹침 → 무조건 중복
        if has_core_keyword_overlap(cand_lower, h_lower, threshold=3):
            return True
        # 유사도 기반 판단
        if similarity_score(cand_lower, h_lower) >= threshold:
            return True
    return False


def load_posted_history(days=60) -> set:
    """
    최근 N일 포스팅된 키워드/제목 집합 로드
    포함 경로:
      - output/posts/*_meta.json
      - output/topics/daily_topics_*.json
      - p004-blogger/posts/*.md (yaml frontmatter title:)
      - output/published/*.json
    날짜 파싱 실패해도 무조건 포함
    """
    used = set()
    cutoff = datetime.date.today() - datetime.timedelta(days=days)

    # 1) output/posts/ 의 메타 파일 스캔
    if os.path.exists(POSTS):
        for fname in os.listdir(POSTS):
            if not fname.endswith("_meta.json"):
                continue
            try:
                meta = json.load(open(os.path.join(POSTS, fname), encoding="utf-8"))
                for field in ("title", "primary_keyword", "topic"):
                    val = meta.get(field, "").lower()
                    if val:
                        used.add(val)
            except Exception:
                pass

    # 2) output/topics/ 의 daily_topics 스캔
    if os.path.exists(OUTPUT):
        for fname in os.listdir(OUTPUT):
            if not fname.startswith("daily_topics_") or not fname.endswith(".json"):
                continue
            try:
                date_str = fname.replace("daily_topics_", "").replace(".json", "")
                try:
                    fdate = datetime.date.fromisoformat(date_str)
                    if fdate < cutoff or fdate.isoformat() == TODAY:
                        continue
                except Exception:
                    pass  # 날짜 파싱 실패해도 읽기
                data = json.load(open(os.path.join(OUTPUT, fname), encoding="utf-8"))
                for t in data.get("topics", []):
                    for field in ("query", "final_title"):
                        val = t.get(field, "").lower()
                        if val:
                            used.add(val)
            except Exception:
                pass

    # 3) p004-blogger/posts/*.md — yaml frontmatter title: 필드 추출
    blogger_posts_dir = os.path.join(
        BASE, "..", "p004-blogger", "posts"
    )
    blogger_posts_dir = os.path.normpath(blogger_posts_dir)
    if os.path.exists(blogger_posts_dir):
        for fname in os.listdir(blogger_posts_dir):
            if not fname.endswith(".md"):
                continue
            try:
                fpath = os.path.join(blogger_posts_dir, fname)
                with open(fpath, encoding="utf-8", errors="replace") as f:
                    content = f.read(4096)  # frontmatter만 읽으면 충분
                # yaml frontmatter 파싱 (--- ... --- 블록)
                fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
                if fm_match:
                    fm_text = fm_match.group(1)
                    title_match = re.search(r"^title\s*:\s*['\"]?(.*?)['\"]?\s*$",
                                            fm_text, re.MULTILINE)
                    if title_match:
                        title = title_match.group(1).strip().lower()
                        if title:
                            used.add(title)
            except Exception:
                pass

    # 4) output/published/*.json
    published_dir = os.path.join(BASE, "output", "published")
    if os.path.exists(published_dir):
        for fname in os.listdir(published_dir):
            if not fname.endswith(".json"):
                continue
            try:
                data = json.load(open(os.path.join(published_dir, fname), encoding="utf-8"))
                # 가능한 필드 전부 수집
                for field in ("title", "primary_keyword", "topic", "query", "final_title"):
                    val = data.get(field, "")
                    if isinstance(val, str) and val:
                        used.add(val.lower())
            except Exception:
                pass

    print(f"  [중복방지] 이력 {len(used)}개 로드 (최근 {days}일 + 블로거 포스트 + published)")
    return used


# ── 실시간 트렌드 기반 키워드 생성 ───────────────────────────────────────────

def generate_trending_queries() -> list:
    """
    AI 도메인별 최신 뉴스를 수집해 실제 트렌딩 헤드라인 기반 쿼리 생성
    - 날짜 seed 기반 20개 도메인만 사용 (전체 순환 보장)
    - arXiv 주간 논문도 후보에 추가
    """
    queries = []
    print("  [트렌드 수집] 도메인별 최신 뉴스 기반 쿼리 생성...")

    # arXiv 주간 논문 후보 먼저 추가
    arxiv_candidates = fetch_arxiv_weekly()
    queries.extend(arxiv_candidates)
    print(f"  [arXiv Weekly] {len(arxiv_candidates)}개 논문 후보 추가")

    # 오늘의 20개 도메인 (로테이션)
    todays_domains = get_todays_domains()
    print(f"  [도메인 로테이션] 오늘의 도메인 {len(todays_domains)}개: {', '.join(todays_domains[:5])}...")

    for domain in todays_domains:
        news = fetch_gnews(domain, max_results=3)
        if news:
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
    - 최신 뉴스 건수 (x3) + 웹 결과 풍부도 + 논문 + HackerNews + Reddit
    - 중복 시 점수 -1 처리
    - 포지셔닝 필드 추가
    """
    query  = cand["query"]
    domain = cand.get("domain", "")

    # 포지셔닝 결정
    positioning = DOMAIN_POSITIONING.get(domain, "트렌드분석")

    # 중복 검사
    if is_duplicate(query, history):
        return {
            **cand,
            "score": -1,
            "duplicate": True,
            "news": [], "web": [], "papers": [],
            "hn": [], "reddit": [],
            "positioning": positioning,
        }

    news   = fetch_gnews(query, max_results=5)
    web    = brave_search(query, count=5)
    papers = fetch_arxiv(re.sub(r"[^\w\s가-힣]", "", query)[:50], max_results=2)
    hn     = fetch_hackernews(query, max_results=5)
    reddit = fetch_reddit_ai(query, max_results=5)

    # 뉴스 신선도
    fresh_news = 0
    today_str = TODAY
    yesterday_str = (datetime.date.today() - datetime.timedelta(1)).isoformat()
    for n in news:
        pd = n.get("pubdate", "")
        if pd and any(x in pd for x in ["today", today_str, yesterday_str]):
            fresh_news += 2
        else:
            fresh_news += 1

    news_score   = fresh_news
    web_score    = len(web)
    paper_score  = len(papers) * 2
    source_bonus = 3 if cand.get("source") == "gnews" else 0
    hn_score     = len(hn) * 2
    reddit_score = len(reddit)

    total = news_score * 3 + web_score + paper_score + source_bonus + hn_score + reddit_score

    time.sleep(0.4)
    return {
        **cand,
        "score":       total,
        "duplicate":   False,
        "news":        news,
        "web":         web,
        "papers":      papers,
        "hn":          hn,
        "reddit":      reddit,
        "news_score":  news_score,
        "web_score":   web_score,
        "hn_score":    hn_score,
        "reddit_score": reddit_score,
        "positioning": positioning,
    }


def select_top_topics(n=3) -> list:
    """
    중복 없는 상위 n개 주제 선정 (포지셔닝 다양화)
    1번: 뉴스성 최고점
    2번: 기술심층 또는 산업분석 최고점
    3번: 실용가이드 또는 국내이슈 또는 트렌드분석 최고점
    """
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
            pos_label = result.get("positioning", "?")
            print(f"    [{result['score']:3d}점][{pos_label}] {result['query'][:55]}")
        else:
            if result.get("duplicate"):
                print(f"    [중복제외] {result['query'][:60]}")

    # 점수 내림차순 정렬
    scored.sort(key=lambda x: -x["score"])

    # 포지셔닝별 그룹 분리
    groups = {
        "뉴스성":   [],
        "기술심층": [],
        "산업분석": [],
        "실용가이드": [],
        "트렌드분석": [],
        "국내이슈": [],
    }
    for s in scored:
        p = s.get("positioning", "트렌드분석")
        if p in groups:
            groups[p].append(s)

    # 포지셔닝 기반 선정
    selected = []
    used_queries = set()

    def pick_best(group_keys: list) -> dict | None:
        """여러 포지셔닝 그룹 중 최고 점수 후보 반환"""
        best = None
        for key in group_keys:
            for cand in groups.get(key, []):
                if cand["query"] in used_queries:
                    continue
                if best is None or cand["score"] > best["score"]:
                    best = cand
        return best

    # 1번: 뉴스성
    pick1 = pick_best(["뉴스성"])
    if pick1:
        selected.append(pick1)
        used_queries.add(pick1["query"])

    # 2번: 기술심층 or 산업분석
    pick2 = pick_best(["기술심층", "산업분석"])
    if pick2:
        selected.append(pick2)
        used_queries.add(pick2["query"])

    # 3번: 실용가이드 or 국내이슈 or 트렌드분석
    pick3 = pick_best(["실용가이드", "국내이슈", "트렌드분석"])
    if pick3:
        selected.append(pick3)
        used_queries.add(pick3["query"])

    # 부족하면 점수 최고 후보로 fallback
    if len(selected) < n:
        for s in scored:
            if s["query"] not in used_queries:
                selected.append(s)
                used_queries.add(s["query"])
            if len(selected) >= n:
                break

    # 그래도 부족하면 도메인 중복 허용
    if len(selected) < n:
        for s in scored:
            if s not in selected:
                selected.append(s)
            if len(selected) >= n:
                break

    print(f"\n  [최종 선정] {len(selected)}개:")
    for i, t in enumerate(selected, 1):
        print(f"    {i}. [{t['score']}점][{t.get('positioning','?')}][{t['domain']}] {t['query'][:55]}")

    return selected[:n]


def build_topic_package(topic_data: dict) -> dict:
    """상세 자료 수집 + 포지셔닝 + content_angle 포함"""
    query       = topic_data["query"]
    positioning = topic_data.get("positioning", "트렌드분석")

    print(f"  [상세 수집] [{positioning}] {query[:60]}")

    extra_web    = brave_search(f"{query} 완벽 가이드 2025", count=8)
    extra_papers = fetch_arxiv(query[:50], max_results=3)
    github       = fetch_github_trending()
    producthunt  = fetch_producthunt_ai(max_results=5)

    # content_angle 자동 생성
    content_angle = CONTENT_ANGLES.get(positioning, "트렌드 배경 → 데이터 근거 → 시사점 → 미래 예측")

    return {
        "query":         query,
        "domain":        topic_data.get("domain", ""),
        "source":        topic_data.get("source", ""),
        "score":         topic_data["score"],
        "positioning":   positioning,
        "content_angle": content_angle,
        "news":          topic_data.get("news", []),
        "web":           topic_data.get("web", []) + extra_web,
        "papers":        topic_data.get("papers", []) + extra_papers,
        "hn":            topic_data.get("hn", []),
        "reddit":        topic_data.get("reddit", []),
        "producthunt":   producthunt,
        "github":        github,
        "collected_at":  datetime.datetime.utcnow().isoformat(),
    }


# ── 메인 ─────────────────────────────────────────────────────────────────────

def run():
    print(f"[Research Agent v2] {TODAY} 시작")
    print(f"  도메인 총 {len(AI_DOMAINS)}개, 오늘 로테이션: {DAILY_DOMAINS_COUNT}개")

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

    print(f"\n[Research Agent v2] 완료 → {output_path}")
    return result


if __name__ == "__main__":
    run()
