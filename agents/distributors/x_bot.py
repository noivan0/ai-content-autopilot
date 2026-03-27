"""
X(트위터) 배포봇 — P004 버전 (agents/distributors/x_bot.py)
역할: X 스레드 JSON → X API v2로 순차 트윗 게시
자격증명 없으면 graceful skip.

사전 조건:
- X Developer 계정 + 앱 등록
- .env: X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET

ref: sinmb79/blog-writer bots/distributors/x_bot.py
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

X_API_KEY = os.getenv('X_API_KEY', '')
X_API_SECRET = os.getenv('X_API_SECRET', '')
X_ACCESS_TOKEN = os.getenv('X_ACCESS_TOKEN', '')
X_ACCESS_SECRET = os.getenv('X_ACCESS_SECRET', '')

X_API_V2 = 'https://api.twitter.com/2/tweets'


def _check_credentials() -> bool:
    if not all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET]):
        logger.info("X API 자격증명 없음 (.env: X_API_KEY 등) — 건너뜀")
        return False
    return True


def _get_auth():
    try:
        from requests_oauthlib import OAuth1
        return OAuth1(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET)
    except ImportError:
        logger.error("requests-oauthlib 미설치. pip install requests-oauthlib")
        return None


def post_tweet(text: str, reply_to_id: str = '') -> str:
    """단일 트윗 게시. Returns: 트윗 ID"""
    if not _check_credentials():
        return ''
    auth = _get_auth()
    if not auth:
        return ''

    payload = {'text': text}
    if reply_to_id:
        payload['reply'] = {'in_reply_to_tweet_id': reply_to_id}

    try:
        import requests
        resp = requests.post(X_API_V2, json=payload, auth=auth, timeout=15)
        resp.raise_for_status()
        tweet_id = resp.json().get('data', {}).get('id', '')
        logger.info(f"트윗 게시: {tweet_id} ({len(text)}자)")
        return tweet_id
    except Exception as e:
        logger.error(f"트윗 게시 실패: {e}")
        return ''


def publish_thread(article: dict, thread_data: list) -> bool:
    """
    스레드 JSON → 순차 트윗 게시.
    thread_data: thread_converter.convert() 반환값
    자격증명 없으면 False (graceful skip).
    """
    if not _check_credentials():
        return False

    title = article.get('title', '')
    logger.info(f"X 스레드 발행 시작: {title} ({len(thread_data)}개 트윗)")

    prev_id = ''
    tweet_ids = []
    for tweet in sorted(thread_data, key=lambda x: x['order']):
        text = tweet['text']
        tweet_id = post_tweet(text, prev_id)
        if not tweet_id:
            logger.error(f"스레드 중단: {tweet['order']}번 트윗 실패")
            return False
        tweet_ids.append(tweet_id)
        prev_id = tweet_id
        time.sleep(1)  # rate limit 방지

    logger.info(f"X 스레드 발행 완료: {len(tweet_ids)}개")
    _log_published(article, tweet_ids[0] if tweet_ids else '', 'x_thread')
    return True


def publish_thread_from_file(article: dict, thread_file: str) -> bool:
    """파일에서 스레드 데이터 로드 후 게시"""
    try:
        data = json.loads(Path(thread_file).read_text(encoding='utf-8'))
        return publish_thread(article, data)
    except Exception as e:
        logger.error(f"스레드 파일 로드 실패: {e}")
        return False


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
    # 자격증명 없이 스레드 구조만 확인
    import sys
    sys.path.insert(0, str(BASE_DIR))
    from agents.converters import thread_converter

    sample = {
        'title': 'ChatGPT o3 완벽 분석',
        'slug': 'chatgpt-o3-analysis',
        'domain': 'ChatGPT OpenAI',
        'corner': 'AI 소식',
        'tags': ['ChatGPT', 'AI'],
        'key_points': ['o3 수학·코딩 인간 전문가', 'API 비용 6배', '멀티모달 지원'],
    }
    threads = thread_converter.convert(sample, save_file=False)
    for t in threads:
        print(f"[{t['order']}] {t['text']}\n")
