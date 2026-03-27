"""
유튜브 배포봇 — P004 버전 (agents/distributors/youtube_bot.py)
역할: 쇼츠 MP4 → YouTube Data API v3 업로드
자격증명(token.json) 없으면 graceful skip.

사전 조건:
- Google Cloud에서 YouTube Data API v3 활성화
- .env: YOUTUBE_CHANNEL_ID
- token.json: 기존 Google OAuth (Blogger와 동일)

ref: sinmb79/blog-writer bots/distributors/youtube_bot.py
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
LOG_DIR = BASE_DIR / 'output' / 'logs'
DATA_DIR = BASE_DIR / 'output' / 'published'
TOKEN_PATH = BASE_DIR / 'token.json'
LOG_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.FileHandler(LOG_DIR / 'distributor.log', encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)

YOUTUBE_CHANNEL_ID = os.getenv('YOUTUBE_CHANNEL_ID', '')

YOUTUBE_SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube',
]

# P004 코너 → YouTube 태그 매핑
CORNER_TAGS = {
    'AI 소식':    ['AI소식', 'AI뉴스', 'AI인사이트', 'Shorts', '인공지능'],
    'AI 분석':    ['AI분석', 'LLM', 'AI인사이트', 'Shorts', '딥러닝'],
    'AI 활용':    ['AI활용', 'AI도구', 'AI인사이트', 'Shorts', '생산성'],
    'AI 개발':    ['AI개발', 'AIcoding', 'AI인사이트', 'Shorts', '개발자'],
    'AI 인사이트': ['AI인사이트', 'AI', 'Shorts', '인공지능', 'P004'],
}


def _check_credentials() -> bool:
    if not YOUTUBE_CHANNEL_ID:
        logger.info("YOUTUBE_CHANNEL_ID 없음 — YouTube 건너뜀")
        return False
    if not TOKEN_PATH.exists():
        logger.info("token.json 없음 — YouTube 건너뜀 (scripts/setup_oauth.py 먼저 실행)")
        return False
    return True


def _get_credentials():
    """기존 Google OAuth token.json 재사용"""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), YOUTUBE_SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                TOKEN_PATH.write_text(creds.to_json())
        return creds
    except Exception as e:
        logger.error(f"YouTube 인증 실패: {e}")
        return None


def build_video_metadata(article: dict) -> dict:
    """유튜브 업로드용 메타데이터 구성"""
    title = article.get('title', '')
    meta = article.get('meta', article.get('meta_description', ''))
    corner = article.get('corner', 'AI 인사이트')
    key_points = article.get('key_points', [])

    description_parts = [meta, '']
    if key_points:
        for point in key_points[:3]:
            description_parts.append(f'• {point}')
        description_parts.append('')

    blog_url = os.getenv('BLOG_URL', 'https://ai-insight-blog.blogspot.com')
    description_parts.append(blog_url)
    description_parts.append('#Shorts #AI #인공지능')

    tags = CORNER_TAGS.get(corner, ['AI인사이트', 'Shorts', 'AI']) + ['Shorts', 'AI']

    return {
        'snippet': {
            'title': f'{title[:90]} #Shorts',
            'description': '\n'.join(description_parts),
            'tags': list(dict.fromkeys(tags)),  # 중복 제거
            'categoryId': '28',  # Science & Technology
        },
        'status': {
            'privacyStatus': 'public',
            'selfDeclaredMadeForKids': False,
        },
    }


def publish_shorts(article: dict, video_path: str) -> bool:
    """
    쇼츠 MP4 → YouTube 업로드.
    자격증명 없으면 False (graceful skip).
    """
    if not _check_credentials():
        return False

    if not Path(video_path).exists():
        logger.error(f"영상 파일 없음: {video_path}")
        return False

    logger.info(f"YouTube 쇼츠 발행 시작: {article.get('title', '')}")

    creds = _get_credentials()
    if not creds:
        return False

    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        service = build('youtube', 'v3', credentials=creds)
        metadata = build_video_metadata(article)

        media = MediaFileUpload(
            video_path,
            mimetype='video/mp4',
            resumable=True,
            chunksize=5 * 1024 * 1024,
        )

        request = service.videos().insert(
            part='snippet,status',
            body=metadata,
            media_body=media,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                logger.info(f"업로드 진행: {pct}%")

        video_id = response.get('id', '')
        video_url = f'https://www.youtube.com/shorts/{video_id}'
        logger.info(f"YouTube 쇼츠 발행 완료: {video_url}")

        _log_published(article, video_id, 'youtube_shorts', video_url)
        return True

    except Exception as e:
        logger.error(f"YouTube 업로드 실패: {e}")
        return False


def _log_published(article: dict, post_id: str, platform: str, url: str = ''):
    record = {
        'platform': platform,
        'post_id': post_id,
        'url': url,
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
        'meta': 'ChatGPT o3 성능, 비용, 활용법 완벽 분석',
        'slug': 'chatgpt-o3-analysis',
        'corner': 'AI 소식',
        'key_points': ['수학·코딩 인간 전문가 수준', 'API 비용 6배', '멀티모달 지원'],
    }
    import pprint
    pprint.pprint(build_video_metadata(sample))
