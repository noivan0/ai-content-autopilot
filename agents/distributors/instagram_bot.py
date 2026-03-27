"""
인스타그램 배포봇 — P004 버전 (agents/distributors/instagram_bot.py)
역할: 카드 이미지 → Instagram Graph API 업로드
자격증명 없으면 graceful skip.

사전 조건:
- Facebook Page + Instagram Business 계정 연결
- .env: INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_ACCOUNT_ID

ref: sinmb79/blog-writer bots/distributors/instagram_bot.py
"""
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
LOG_DIR = BASE_DIR / 'output' / 'logs'
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
INSTAGRAM_ACCOUNT_ID = os.getenv('INSTAGRAM_ACCOUNT_ID', '')
GRAPH_API_BASE = 'https://graph.facebook.com/v19.0'

BLOG_URL = os.getenv('BLOG_URL', 'https://ai-insight-blog.blogspot.com')
BRAND_TAG = '#AI인사이트 #인공지능 #LLM #P004'


def _check_credentials() -> bool:
    if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_ACCOUNT_ID:
        logger.info("Instagram 자격증명 없음 (.env: INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_ACCOUNT_ID) — 건너뜀")
        return False
    return True


def build_caption(article: dict) -> str:
    """인스타그램 캡션 생성"""
    title = article.get('title', '')
    corner = article.get('corner', '')
    key_points = article.get('key_points', [])
    tags = article.get('tags', [])

    lines = [f"✨ {title}", ""]
    if key_points:
        for point in key_points[:3]:
            lines.append(f"• {point}")
        lines.append("")

    lines.append("전체 내용: 프로필 링크 🔗")
    lines.append("")

    hashtags = [f'#{corner.replace(" ", "")}'] if corner else []
    hashtags += [f'#{t}' for t in tags[:5] if t]
    hashtags.append(BRAND_TAG)
    lines.append(' '.join(hashtags))

    return '\n'.join(lines)


def upload_image_container(image_url: str, caption: str) -> str:
    """인스타 이미지 컨테이너 생성. Returns: container_id"""
    if not _check_credentials():
        return ''
    try:
        import requests
        url = f"{GRAPH_API_BASE}/{INSTAGRAM_ACCOUNT_ID}/media"
        params = {
            'image_url': image_url,
            'caption': caption,
            'access_token': INSTAGRAM_ACCESS_TOKEN,
        }
        resp = requests.post(url, data=params, timeout=30)
        resp.raise_for_status()
        container_id = resp.json().get('id', '')
        logger.info(f"이미지 컨테이너 생성: {container_id}")
        return container_id
    except Exception as e:
        logger.error(f"Instagram 컨테이너 생성 실패: {e}")
        return ''


def publish_container(container_id: str) -> str:
    """컨테이너 → 실제 발행. Returns: post_id"""
    if not _check_credentials() or not container_id:
        return ''
    try:
        import requests
        status_url = f"{GRAPH_API_BASE}/{container_id}"
        for _ in range(12):
            status_resp = requests.get(
                status_url,
                params={'fields': 'status_code', 'access_token': INSTAGRAM_ACCESS_TOKEN},
                timeout=10
            )
            status = status_resp.json().get('status_code', '')
            if status == 'FINISHED':
                break
            if status in ('ERROR', 'EXPIRED'):
                logger.error(f"컨테이너 오류: {status}")
                return ''
            time.sleep(5)

        publish_url = f"{GRAPH_API_BASE}/{INSTAGRAM_ACCOUNT_ID}/media_publish"
        params = {
            'creation_id': container_id,
            'access_token': INSTAGRAM_ACCESS_TOKEN,
        }
        resp = requests.post(publish_url, data=params, timeout=30)
        resp.raise_for_status()
        post_id = resp.json().get('id', '')
        logger.info(f"Instagram 발행 완료: {post_id}")
        return post_id
    except Exception as e:
        logger.error(f"Instagram 발행 실패: {e}")
        return ''


def publish_card(article: dict, image_path_or_url: str) -> bool:
    """
    카드 이미지를 인스타그램 피드에 게시.
    image_path_or_url: 로컬 경로 또는 공개 URL
    자격증명 없으면 False 반환 (graceful skip).
    """
    if not _check_credentials():
        return False

    logger.info(f"Instagram 발행 시작: {article.get('title', '')}")

    image_url = image_path_or_url
    if not image_path_or_url.startswith('http'):
        try:
            from agents.distributors.image_host import get_public_url
        except ImportError:
            from image_host import get_public_url
        image_url = get_public_url(image_path_or_url)
        if not image_url:
            logger.error("공개 URL 변환 실패 — .env에 IMGBB_API_KEY 설정 필요")
            return False

    caption = build_caption(article)
    container_id = upload_image_container(image_url, caption)
    if not container_id:
        return False

    post_id = publish_container(container_id)
    if not post_id:
        return False

    _log_published(article, post_id, 'instagram_card')
    return True


def _log_published(article: dict, post_id: str, platform: str):
    record = {
        'platform': platform,
        'post_id': post_id,
        'title': article.get('title', ''),
        'corner': article.get('corner', ''),
        'published_at': datetime.now().isoformat(),
    }
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{platform}_{post_id}.json"
    with open(DATA_DIR / filename, 'w', encoding='utf-8') as f:
        json.dump(record, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    sample = {
        'title': 'ChatGPT o3 완벽 분석',
        'corner': 'AI 소식',
        'key_points': ['o3 수학·코딩 인간 전문가 수준', 'API 비용 6배', '멀티모달 지원'],
        'tags': ['AI', 'ChatGPT'],
    }
    print(build_caption(sample))
