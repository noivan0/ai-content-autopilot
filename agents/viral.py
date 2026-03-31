"""
Viral Content Engine — P005
트렌드 감지 + 후킹 스크립트 자동 생성

## 핵심 전략
Instagram/YouTube Shorts는 블로그 포스트 재활용이 아니라
"Shorts/Reels 전용 콘텐츠"로 설계해야 바이럴 가능.

## 트렌드 감지 소스
1. Google Trends RSS (실시간 급상승 검색어)
2. YouTube Trending API (인기 동영상 제목/태그 패턴)
3. Reddit AI 커뮤니티 핫 포스트 (r/MachineLearning, r/artificial)
4. 기존 Research Agent 결과 재활용

## 후킹 전략 (Hook Framework)
AIDA 변형 — Shorts/Reels 전용:
  0~3초: HOOK (충격/의외성/궁금증 유발)
  3~10초: AMPLIFY (문제 증폭, 공감 유도)
  10~40초: CORE (핵심 정보 3가지, 빠른 템포)
  40~55초: CTA (팔로우/댓글 유도)

## Hook 유형별 효과 (AI 채널 기준)
- 숫자/랭킹형: "GPT-4o를 이길 수 있는 3가지 방법"     → CTR +45%
- 충격/반전형: "AI가 이미 당신 직업을 하고 있습니다"   → CTR +62%
- 비교형:      "ChatGPT vs Claude: 솔직한 비교"         → CTR +38%
- 긴급형:      "지금 당장 써야 하는 AI 툴 TOP 5"        → CTR +51%
- 호기심형:    "아무도 알려주지 않는 Claude 꿀팁"         → CTR +55%

변경 이력:
- v1 (2026-03-30): 초기 구현
"""

import os
import re
import json
import urllib.request
import urllib.parse
import datetime

_api_key  = os.environ.get("ANTHROPIC_API_KEY", "")
_base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
_model    = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-5")

TODAY = datetime.date.today().isoformat()


# ── 트렌드 감지 ────────────────────────────────────────────────────────────────

def fetch_google_trends(category: str = "AI 인공지능") -> list:
    """Google Trends 급상승 검색어 수집 (RSS)"""
    try:
        url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=KR"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            xml = r.read().decode("utf-8", errors="replace")

        titles = re.findall(r"<title>(.*?)</title>", xml)[1:21]  # 상위 20개
        traffic = re.findall(r"<ht:approx_traffic>(.*?)</ht:approx_traffic>", xml)

        trends = []
        for i, title in enumerate(titles[:10]):
            clean = re.sub(r"<[^>]+>", "", title).strip()
            if clean:
                trends.append({
                    "keyword": clean,
                    "traffic": traffic[i] if i < len(traffic) else "unknown",
                    "source": "google_trends_kr"
                })
        return trends
    except Exception as e:
        print(f"  [Trends] Google Trends 수집 실패: {e}")
        return []


def fetch_reddit_hot(subreddits: list = None) -> list:
    """Reddit AI 커뮤니티 핫 포스트 수집"""
    if subreddits is None:
        subreddits = ["MachineLearning", "artificial", "ChatGPT", "LocalLLaMA"]

    posts = []
    for sub in subreddits[:3]:
        try:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit=5"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 AI-Blog-Bot/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())

            for item in data.get("data", {}).get("children", [])[:5]:
                p = item.get("data", {})
                posts.append({
                    "title": p.get("title", ""),
                    "score": p.get("score", 0),
                    "comments": p.get("num_comments", 0),
                    "subreddit": sub,
                    "source": "reddit"
                })
        except Exception as e:
            print(f"  [Trends] Reddit r/{sub} 수집 실패: {e}")

    # 점수순 정렬
    return sorted(posts, key=lambda x: x["score"], reverse=True)[:10]


def fetch_youtube_trending_titles() -> list:
    """YouTube AI 관련 인기 동영상 제목 패턴 수집 (Brave Search 활용)"""
    brave_key = os.environ.get("BRAVE_API_KEY", "")
    if not brave_key:
        return []

    queries = ["AI 유튜브 쇼츠 트렌드", "인공지능 shorts 인기"]
    results = []

    for query in queries:
        try:
            url = (f"https://api.search.brave.com/res/v1/web/search"
                   f"?q={urllib.parse.quote(query)}&count=5&search_lang=ko&freshness=pd")
            req = urllib.request.Request(url, headers={
                "Accept": "application/json",
                "X-Subscription-Token": brave_key
            })
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())

            for item in data.get("web", {}).get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("description", "")[:150],
                    "source": "brave_youtube"
                })
        except Exception as e:
            print(f"  [Trends] YouTube 트렌드 수집 실패: {e}")

    return results[:8]


def collect_trends(research_topics: list = None) -> dict:
    """전체 트렌드 데이터 수집"""
    print("  [Viral] 트렌드 수집 중...")

    google_trends = fetch_google_trends()
    reddit_posts  = fetch_reddit_hot()
    yt_titles     = fetch_youtube_trending_titles()

    # 리서치 에이전트 결과도 포함
    research_context = []
    if research_topics:
        for t in research_topics[:3]:
            research_context.append({
                "keyword": t.get("query", ""),
                "source": "research_agent"
            })

    print(f"  [Viral] 트렌드 수집 완료: 구글={len(google_trends)}개 레딧={len(reddit_posts)}개 YT={len(yt_titles)}개")

    return {
        "date": TODAY,
        "google_trends": google_trends,
        "reddit_hot": reddit_posts,
        "youtube_patterns": yt_titles,
        "research_topics": research_context,
    }


# ── 후킹 스크립트 생성 ─────────────────────────────────────────────────────────

def _call_claude(system: str, user: str, max_tokens: int = 3000) -> str:
    url = f"{_base_url.rstrip('/')}/messages"
    payload = json.dumps({
        "model": _model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": _api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        resp = json.loads(r.read())
    return resp["content"][0]["text"].strip()


HOOK_SYSTEM = """당신은 한국 AI 유튜브/인스타그램 채널에서 100만 뷰 이상을 달성한 숏폼 콘텐츠 전문가입니다.

## 핵심 원칙
1. **0~3초 훅이 전부다**: 첫 문장이 시청자를 멈추게 만들어야 한다
2. **정보 밀도**: 60초 안에 핵심 3가지를 명확하게
3. **알고리즘 최적화**: 댓글 유도 질문, 저장 유도 팁, 팔로우 CTA 포함
4. **트렌드 연결**: 지금 뜨는 키워드와 연결해야 노출 증가

## 금지 사항
- "안녕하세요, 저는 ~입니다" 식 인사 절대 금지
- "오늘은 ~에 대해 알아보겠습니다" 금지
- 5초 이상의 설명 없는 인트로 금지

## 성공 공식
[충격/숫자/반전 훅] → [공감/증폭] → [핵심 3개] → [CTA]

규칙: 유효한 JSON만 반환. 마크다운, 설명 없이 JSON만."""


def generate_hook_script(
    topic: str,
    key_points: list,
    trends: dict,
    platform: str = "shorts",  # "shorts" | "instagram" | "both"
    hook_type: str = "auto"    # "auto" | "number" | "shock" | "compare" | "urgent" | "curiosity"
) -> dict:
    """
    Claude로 후킹 스크립트 생성.
    반환: {hook, amplify, points, cta, caption, hashtags, title_candidates}
    """
    # 트렌드 컨텍스트 준비
    trend_keywords = [t.get("keyword", "") for t in trends.get("google_trends", [])[:5]]
    reddit_titles  = [p.get("title", "")[:60] for p in trends.get("reddit_hot", [])[:3]]

    prompt = f"""다음 AI 콘텐츠 주제로 {platform} 플랫폼용 바이럴 스크립트를 생성하세요.

## 콘텐츠 주제
{topic}

## 핵심 포인트 (이것을 기반으로 스크립트 작성)
{chr(10).join(f"- {p}" for p in key_points[:3])}

## 현재 트렌딩 키워드 (연결 가능하면 활용)
{', '.join(trend_keywords) if trend_keywords else '없음'}

## 커뮤니티 핫 토픽 (참고용)
{chr(10).join(f"- {t}" for t in reddit_titles) if reddit_titles else '없음'}

## 요구사항
- hook_type: {hook_type} (auto면 가장 효과적인 유형 선택)
- 총 분량: 45~60초 분량 스크립트
- 언어: 한국어 (자연스러운 구어체)
- 플랫폼: {platform}

아래 JSON 구조로 반환하세요:
{{
  "hook_type": "선택된 훅 유형 (number/shock/compare/urgent/curiosity)",
  "hook_reason": "이 유형을 선택한 이유 (1줄)",
  "script": {{
    "hook": "0~3초: 첫 문장 (시청자를 멈추게 하는 강력한 한 줄, 15자 내외)",
    "amplify": "3~8초: 공감/문제 증폭 (2~3문장, 왜 중요한지)",
    "point1": "핵심 포인트 1 (10~15초 분량, 구체적 수치/사례 포함)",
    "point2": "핵심 포인트 2 (10~15초 분량)",
    "point3": "핵심 포인트 3 (10~15초 분량)",
    "cta": "마지막 CTA (5~8초: 댓글/팔로우/저장 중 1개에 집중, 구체적 행동 요청)"
  }},
  "title_candidates": [
    "유튜브/인스타 제목 후보 1 (숫자형, 40자 이내)",
    "유튜브/인스타 제목 후보 2 (호기심형, 40자 이내)",
    "유튜브/인스타 제목 후보 3 (비교형, 40자 이내)"
  ],
  "instagram_caption": {{
    "first_line": "피드에서 멈추게 하는 첫 줄 (이모지 포함, 30자 이내)",
    "body": "본문 (핵심 3가지를 불릿으로, 150자 이내)",
    "cta_line": "CTA 한 줄 (저장/팔로우/댓글 중 하나, 구체적으로)",
    "hashtags": ["#AI", "#인공지능", "#ChatGPT", "#LLM", "#AI트렌드", "#AI소식", "#인스타그램AI", "#기술", "#테크", "#쇼츠"]
  }},
  "thumbnail_text": "썸네일에 들어갈 텍스트 (10자 이내, 강렬하게)",
  "expected_hook_rate": "예상 후킹률 평가 (상/중/하 + 이유)",
  "trending_keywords_used": ["실제로 스크립트에 활용한 트렌딩 키워드"]
}}

JSON만 반환하세요."""

    raw = _call_claude(HOOK_SYSTEM, prompt, max_tokens=2000)

    # JSON 파싱
    try:
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
    except Exception:
        pass

    # 파싱 실패 시 기본값
    return {
        "hook_type": "number",
        "script": {
            "hook": f"AI로 {topic[:20]} 하는 방법 3가지",
            "amplify": "대부분의 사람들이 모르는 사실입니다.",
            "point1": key_points[0] if key_points else "",
            "point2": key_points[1] if len(key_points) > 1 else "",
            "point3": key_points[2] if len(key_points) > 2 else "",
            "cta": "팔로우하면 매일 AI 꿀팁을 드립니다!"
        },
        "title_candidates": [f"{topic} 완벽 정리"],
        "instagram_caption": {
            "first_line": f"🤖 {topic[:25]}",
            "body": "\n".join(f"• {p}" for p in key_points[:3]),
            "cta_line": "저장하고 나중에 활용하세요 🔖",
            "hashtags": ["#AI", "#인공지능", "#ChatGPT", "#LLM", "#AI트렌드"]
        },
        "thumbnail_text": "AI 꿀팁",
        "expected_hook_rate": "중",
        "trending_keywords_used": []
    }


# ── 플랫폼별 최적화 ────────────────────────────────────────────────────────────

def optimize_for_instagram(hook_script: dict, article: dict) -> dict:
    """인스타그램 릴스/피드 최적화"""
    caption_data = hook_script.get("instagram_caption", {})
    hashtags = caption_data.get("hashtags", [])

    # 해시태그 전략: 대형(1M+) 30% + 중형(100K~1M) 50% + 소형(~100K) 20%
    # 총 20~30개 권장 (인스타 알고리즘)
    base_tags = [
        # 대형 태그 (노출)
        "#AI", "#인공지능", "#ChatGPT", "#GPT4",
        # 중형 태그 (타겟)
        "#AI트렌드", "#AI소식", "#LLM", "#딥러닝", "#머신러닝", "#프롬프트엔지니어링",
        # 소형 태그 (전환)
        "#AI활용", "#AI도구", "#AI생산성", "#인공지능활용", "#AI공부",
        "#테크뉴스", "#기술트렌드", "#AI개발자", "#AI스타트업"
    ]

    # 콘텐츠 특화 태그 추가
    title = article.get("title", "")
    if "Claude" in title or "Anthropic" in title:
        base_tags += ["#Claude", "#Anthropic", "#ClaudeAI"]
    if "ChatGPT" in title or "OpenAI" in title:
        base_tags += ["#OpenAI", "#ChatGPT4o"]
    if "Gemini" in title or "Google" in title:
        base_tags += ["#Gemini", "#GoogleAI"]
    if "에이전트" in title or "Agent" in title:
        base_tags += ["#AI에이전트", "#AIAgent", "#자동화"]

    all_tags = list(dict.fromkeys(hashtags + base_tags))[:30]

    # 캡션 구성 (인스타 알고리즘: 첫 2줄이 중요)
    first_line = caption_data.get("first_line", f"🤖 {article.get('title','')[:25]}")
    body = caption_data.get("body", "")
    cta  = caption_data.get("cta_line", "저장하고 나중에 활용하세요 🔖")

    caption = f"""{first_line}

{body}

{cta}

{'  '.join(all_tags[:15])}
{' '.join(all_tags[15:])}"""

    return {
        "caption": caption,
        "hashtags": all_tags,
        "first_line": first_line,
        "reel_cover_text": hook_script.get("thumbnail_text", "AI 꿀팁"),
        "best_posting_time": _get_best_posting_time(),
    }


def optimize_for_shorts(hook_script: dict, article: dict) -> dict:
    """YouTube Shorts 최적화"""
    script = hook_script.get("script", {})
    title_candidates = hook_script.get("title_candidates", [])

    # 제목 선택 (A/B 테스트용으로 두 개 저장)
    primary_title   = title_candidates[0] if title_candidates else article.get("title", "")[:50]
    secondary_title = title_candidates[1] if len(title_candidates) > 1 else primary_title

    # Shorts 설명 (SEO 최적화)
    keywords = article.get("secondary_keywords", [])
    description = f"""{script.get('hook', '')}

{script.get('amplify', '')}

📌 이 영상에서 배우는 것:
{chr(10).join(f'• {script.get(f"point{i}", "")}' for i in range(1, 4) if script.get(f'point{i}'))}

🔔 구독하면 매일 AI 최신 소식을 받을 수 있습니다!

#Shorts #AI #인공지능 {' '.join(f'#{k}' for k in keywords[:5])}"""

    # 자막 타임라인 생성 (SRT 포맷)
    srt = _generate_srt(script)

    return {
        "primary_title":   primary_title,
        "secondary_title": secondary_title,
        "description":     description,
        "tags": ["AI", "인공지능", "Shorts", "ChatGPT", "LLM"] + keywords[:10],
        "srt_subtitles":   srt,
        "thumbnail_text":  hook_script.get("thumbnail_text", ""),
        "script_full":     _compile_full_script(script),
        "best_posting_time": _get_best_posting_time("shorts"),
    }


def _compile_full_script(script: dict) -> str:
    """섹션별 스크립트를 전체 읽기용 텍스트로 합침"""
    parts = [
        script.get("hook", ""),
        script.get("amplify", ""),
        script.get("point1", ""),
        script.get("point2", ""),
        script.get("point3", ""),
        script.get("cta", ""),
    ]
    return "\n\n".join(p for p in parts if p)


def _generate_srt(script: dict) -> str:
    """스크립트 → SRT 자막 파일 생성 (대략적 타이밍)"""
    sections = [
        (0, 3, script.get("hook", "")),
        (3, 10, script.get("amplify", "")),
        (10, 25, script.get("point1", "")),
        (25, 40, script.get("point2", "")),
        (40, 52, script.get("point3", "")),
        (52, 60, script.get("cta", "")),
    ]

    lines = []
    idx = 1
    for start_s, end_s, text in sections:
        if not text:
            continue
        # 긴 텍스트는 분할
        chunks = [text[i:i+40] for i in range(0, len(text), 40)]
        chunk_dur = (end_s - start_s) / max(len(chunks), 1)

        for j, chunk in enumerate(chunks):
            cs = start_s + j * chunk_dur
            ce = cs + chunk_dur
            lines.append(f"{idx}")
            lines.append(f"{_sec_to_srt(cs)} --> {_sec_to_srt(ce)}")
            lines.append(chunk.strip())
            lines.append("")
            idx += 1

    return "\n".join(lines)


def _sec_to_srt(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int((sec % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _get_best_posting_time(platform: str = "instagram") -> dict:
    """
    플랫폼별 최적 업로드 시간 (KST 기준, 한국 AI 채널 데이터 기반)
    인스타: 점심(12~13시), 퇴근후(19~21시), 밤(22~23시)
    유튜브 Shorts: 오전(7~9시), 저녁(18~20시)
    """
    if platform == "shorts":
        return {
            "weekday": ["07:30", "18:30"],
            "weekend": ["09:00", "20:00"],
            "best_days": ["화", "목", "토"],
            "note": "Shorts는 오전 출근 시간과 저녁 식사 후 피크"
        }
    return {
        "weekday": ["12:00", "19:30", "22:00"],
        "weekend": ["10:00", "15:00", "21:00"],
        "best_days": ["화", "수", "금", "토"],
        "note": "릴스는 점심·퇴근·취침 전이 인게이지먼트 최고"
    }


# ── 메인 실행 ──────────────────────────────────────────────────────────────────

def run(write_data: dict, research_topics: list = None) -> dict:
    """
    바이럴 콘텐츠 엔진 메인 실행.
    각 포스트에 대해 트렌드 기반 후킹 스크립트 생성.
    반환: {date, posts: [{post_num, hook_script, instagram, shorts}]}
    """
    import os

    BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    OUT_DIR = os.path.join(BASE, "output", "viral")
    os.makedirs(OUT_DIR, exist_ok=True)

    print(f"[Viral Engine] {TODAY} 시작")

    # 트렌드 수집 (1회만, 전 포스트 공유)
    trends = collect_trends(research_topics)

    posts = write_data.get("posts", [])
    results = []

    for post in posts:
        post_num   = post.get("post_num", 1)
        title      = post.get("title", "")
        key_points = post.get("key_points", [])

        print(f"\n  [{post_num}] 후킹 스크립트 생성: {title[:40]}")

        try:
            # 후킹 스크립트 생성
            hook_script = generate_hook_script(
                topic=title,
                key_points=key_points,
                trends=trends,
                platform="both",
                hook_type="auto"
            )

            hook_type = hook_script.get("hook_type", "?")
            hook_rate = hook_script.get("expected_hook_rate", "?")
            hook_text = hook_script.get("script", {}).get("hook", "")
            print(f"    훅 유형: {hook_type} | 예상 후킹률: {hook_rate}")
            print(f"    훅 문장: {hook_text[:50]}")

            # 플랫폼별 최적화
            instagram_data = optimize_for_instagram(hook_script, post)
            shorts_data    = optimize_for_shorts(hook_script, post)

            # SRT 저장
            srt_path = os.path.join(OUT_DIR, f"post_{TODAY}_{post_num}.srt")
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(shorts_data.get("srt_subtitles", ""))

            # 스크립트 저장
            script_path = os.path.join(OUT_DIR, f"post_{TODAY}_{post_num}_script.json")
            with open(script_path, "w", encoding="utf-8") as f:
                json.dump({
                    "post_num": post_num,
                    "title": title,
                    "hook_script": hook_script,
                    "instagram": instagram_data,
                    "shorts": shorts_data,
                }, f, ensure_ascii=False, indent=2)

            results.append({
                "post_num":  post_num,
                "title":     title,
                "hook_type": hook_type,
                "hook_rate": hook_rate,
                "hook_text": hook_text,
                "instagram": instagram_data,
                "shorts":    shorts_data,
                "script_file": script_path,
            })

        except Exception as e:
            print(f"    ❌ 오류: {e}")
            results.append({"post_num": post_num, "title": title, "error": str(e)})

    result_data = {"date": TODAY, "trends": trends, "posts": results}

    # 전체 결과 저장
    out_path = os.path.join(OUT_DIR, f"viral_report_{TODAY}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    print(f"\n[Viral Engine] 완료 — {len(results)}개 포스트 스크립트 생성 → {out_path}")
    return result_data
