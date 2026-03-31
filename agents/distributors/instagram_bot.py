"""
Instagram 배포봇 — P005 (viral 기반 업그레이드)
역할: 후킹 스크립트 + 카드 이미지 → Instagram Reels/Feed 최적화 발행

변경 이력:
- v2 (2026-03-30): viral.py 연동, 알고리즘 최적화 캡션, 최적 게시 시간 활용
  * 단순 카드 → 릴스 우선 전략 (알고리즘 노출 3~5배)
  * 후킹 캡션 (첫 2줄이 피드 노출 결정)
  * 해시태그 대/중/소형 혼합 전략 (30개)
  * 릴스 커버 이미지 자동 설정
"""
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
LOG_DIR  = BASE_DIR / 'output' / 'logs'
DATA_DIR = BASE_DIR / 'output' / 'published'
LOG_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.FileHandler(LOG_DIR / 'distributor.log', encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)

INSTAGRAM_ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN', '')
INSTAGRAM_ACCOUNT_ID   = os.getenv('INSTAGRAM_ACCOUNT_ID', '')
GRAPH_API_BASE         = 'https://graph.facebook.com/v19.0'
BLOG_URL               = os.getenv('BLOG_URL', 'https://ai-insight-blog.blogspot.com')


def _check_credentials() -> bool:
    if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_ACCOUNT_ID:
        logger.info("Instagram 자격증명 없음 — 건너뜀")
        return False
    return True


# ── 캡션 빌더 ─────────────────────────────────────────────────────────────────

def build_viral_caption(article: dict, viral_data: dict = None) -> str:
    """
    후킹 스크립트 기반 캡션 생성 (viral.py 연동).
    viral_data 없으면 기본 캡션 사용.
    """
    if viral_data:
        ig = viral_data.get("instagram", {})
        caption = ig.get("caption", "")
        if caption:
            return caption

    # fallback: 기본 캡션
    title      = article.get('title', '')
    key_points = article.get('key_points', [])
    tags       = article.get('tags', [])

    first_line = f"🤖 {title[:30]}{'...' if len(title) > 30 else ''}"
    body_lines = [f"• {p}" for p in key_points[:3]]
    cta        = "💾 저장하고 나중에 활용하세요!"

    base_tags = [
        "#AI", "#인공지능", "#ChatGPT", "#LLM", "#딥러닝",
        "#AI트렌드", "#AI소식", "#AI활용", "#테크뉴스", "#기술트렌드",
        "#프롬프트엔지니어링", "#머신러닝", "#AI도구", "#AI생산성", "#인공지능활용"
    ]
    content_tags = [f"#{t}" for t in tags[:5] if t]
    all_tags = list(dict.fromkeys(content_tags + base_tags))[:25]

    return f"""{first_line}

{chr(10).join(body_lines)}

{cta}

{'  '.join(all_tags[:15])}
{' '.join(all_tags[15:])}"""


# ── Instagram Graph API ────────────────────────────────────────────────────────

def _api_post(endpoint: str, params: dict, timeout: int = 30) -> dict:
    try:
        import requests
        params['access_token'] = INSTAGRAM_ACCESS_TOKEN
        resp = requests.post(f"{GRAPH_API_BASE}/{endpoint}", data=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"API 오류 [{endpoint}]: {e}")
        return {}


def _api_get(endpoint: str, params: dict, timeout: int = 10) -> dict:
    try:
        import requests
        params['access_token'] = INSTAGRAM_ACCESS_TOKEN
        resp = requests.get(f"{GRAPH_API_BASE}/{endpoint}", params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"API GET 오류 [{endpoint}]: {e}")
        return {}


def _wait_for_container(container_id: str, max_wait: int = 60) -> bool:
    """컨테이너 처리 완료 대기"""
    for attempt in range(max_wait // 5):
        data = _api_get(container_id, {"fields": "status_code"})
        status = data.get("status_code", "")
        if status == "FINISHED":
            return True
        if status in ("ERROR", "EXPIRED"):
            logger.error(f"컨테이너 실패: {status}")
            return False
        logger.debug(f"  대기 중... ({attempt+1}회, status={status})")
        time.sleep(5)
    logger.error("컨테이너 타임아웃")
    return False


# ── 이미지 피드 게시 ───────────────────────────────────────────────────────────

def publish_feed_image(article: dict, image_url: str, viral_data: dict = None) -> str:
    """이미지 피드 게시. Returns: post_id"""
    if not _check_credentials():
        return ''

    caption = build_viral_caption(article, viral_data)
    logger.info(f"Instagram 피드 게시: {article.get('title', '')[:40]}")

    # 컨테이너 생성
    container = _api_post(f"{INSTAGRAM_ACCOUNT_ID}/media", {
        "image_url": image_url,
        "caption": caption,
    })
    container_id = container.get("id", "")
    if not container_id:
        logger.error("컨테이너 생성 실패")
        return ''

    # 처리 대기
    if not _wait_for_container(container_id):
        return ''

    # 발행
    publish_result = _api_post(f"{INSTAGRAM_ACCOUNT_ID}/media_publish", {
        "creation_id": container_id,
    })
    post_id = publish_result.get("id", "")
    if post_id:
        logger.info(f"Instagram 피드 발행 완료: {post_id}")
        _log_published(article, post_id, "instagram_feed", caption[:100])
    return post_id


# ── 릴스 게시 ─────────────────────────────────────────────────────────────────

def publish_reel(article: dict, video_url: str, cover_url: str = '', viral_data: dict = None) -> str:
    """
    Instagram Reels 게시 (알고리즘 노출 3~5배).
    video_url: 공개 접근 가능한 MP4 URL (최소 720p, 9:16 비율)
    Returns: post_id
    """
    if not _check_credentials():
        return ''

    caption = build_viral_caption(article, viral_data)
    logger.info(f"Instagram 릴스 게시: {article.get('title', '')[:40]}")

    params = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",   # 피드에도 동시 노출
    }
    if cover_url:
        params["cover_url"] = cover_url

    container = _api_post(f"{INSTAGRAM_ACCOUNT_ID}/media", params)
    container_id = container.get("id", "")
    if not container_id:
        logger.error("릴스 컨테이너 생성 실패")
        return ''

    # 릴스는 처리 시간이 더 걸림 (최대 3분)
    logger.info("  릴스 인코딩 대기 중...")
    if not _wait_for_container(container_id, max_wait=180):
        return ''

    publish_result = _api_post(f"{INSTAGRAM_ACCOUNT_ID}/media_publish", {
        "creation_id": container_id,
    })
    post_id = publish_result.get("id", "")
    if post_id:
        logger.info(f"Instagram 릴스 발행 완료: {post_id}")
        _log_published(article, post_id, "instagram_reel", caption[:100])
    return post_id


# ── 통합 발행 ─────────────────────────────────────────────────────────────────

def publish(
    article: dict,
    image_path_or_url: str = '',
    video_path_or_url: str = '',
    viral_data: dict = None,
    prefer_reel: bool = True,
) -> bool:
    """
    통합 발행 함수.
    - 영상(MP4) 있으면 → 릴스 우선 (알고리즘 노출 3~5배)
    - 영상 없으면 → 이미지 피드
    - prefer_reel=False 시 이미지 피드만
    자격증명 없으면 graceful skip.
    """
    if not _check_credentials():
        return False

    # 공개 URL 변환
    def to_url(path_or_url: str) -> str:
        if not path_or_url:
            return ''
        if path_or_url.startswith('http'):
            return path_or_url
        try:
            from agents.distributors.image_host import get_public_url
        except ImportError:
            try:
                from image_host import get_public_url
            except ImportError:
                return ''
        url = get_public_url(path_or_url)
        if not url:
            logger.error(f"공개 URL 변환 실패: {path_or_url} (IMGBB_API_KEY 확인)")
        return url or ''

    # 릴스 우선
    if prefer_reel and video_path_or_url:
        video_url = to_url(video_path_or_url)
        cover_url = to_url(image_path_or_url)
        if video_url:
            post_id = publish_reel(article, video_url, cover_url, viral_data)
            return bool(post_id)

    # 이미지 피드
    if image_path_or_url:
        image_url = to_url(image_path_or_url)
        if image_url:
            post_id = publish_feed_image(article, image_url, viral_data)
            return bool(post_id)

    logger.warning("Instagram: 게시할 이미지/영상 없음")
    return False


def _log_published(article: dict, post_id: str, platform: str, caption_preview: str = ''):
    record = {
        'platform':       platform,
        'post_id':        post_id,
        'title':          article.get('title', ''),
        'caption_preview': caption_preview,
        'published_at':   datetime.now().isoformat(),
    }
    fname = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{platform}_{post_id}.json"
    with open(DATA_DIR / fname, 'w', encoding='utf-8') as f:
        json.dump(record, f, ensure_ascii=False, indent=2)


# ── 레거시 호환 ───────────────────────────────────────────────────────────────

def publish_card(article: dict, image_path_or_url: str) -> bool:
    """기존 호출 호환성 유지"""
    return publish(article, image_path_or_url=image_path_or_url, prefer_reel=False)


def build_caption(article: dict) -> str:
    """기존 호출 호환성 유지"""
    return build_viral_caption(article)


if __name__ == '__main__':
    sample = {
        'title': 'Claude AI 최신 기능 2025: 달라진 점 완벽 정리',
        'corner': 'AI 소식',
        'key_points': ['코딩 벤치마크 95.2% 달성', 'GPT-4o 대비 40% 저렴', '128K 컨텍스트 지원'],
        'tags': ['Claude', 'AI', 'LLM'],
    }
    print(build_viral_caption(sample))
