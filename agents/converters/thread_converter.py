"""
X 스레드 변환봇 — P004 버전 (agents/converters/thread_converter.py)
역할: article dict → X(트위터) 스레드 JSON
- TITLE + KEY_POINTS → 280자 트윗 3-5개로 분할
- 첫 트윗: 흥미 유발 + 도메인 해시태그
- 중간 트윗: 핵심 포인트
- 마지막 트윗: 블로그 링크 + CTA
출력: output/threads/{date}_{slug}_thread.json

ref: sinmb79/blog-writer bots/converters/thread_converter.py
"""
import json
import logging
import os
import textwrap
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
LOG_DIR = BASE_DIR / 'output' / 'logs'
OUTPUT_DIR = BASE_DIR / 'output' / 'threads'
LOG_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.FileHandler(LOG_DIR / 'converter.log', encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)

BLOG_BASE_URL = os.environ.get('BLOG_URL', 'https://ai-insight-blog.blogspot.com')
TWEET_MAX = 280
BRAND_TAG = '#AI인사이트 #인공지능 #LLM'

# P004 도메인 기반 해시태그
DOMAIN_HASHTAGS = {
    "ChatGPT OpenAI":     "#ChatGPT #OpenAI #AI활용",
    "Claude Anthropic":   "#Claude #Anthropic #LLM",
    "Gemini Google AI":   "#Gemini #Google #AI",
    "Manus AI 에이전트":  "#ManusAI #AI에이전트",
    "LLM 언어모델":       "#LLM #언어모델 #AI",
    "AI 에이전트 자동화": "#AI에이전트 #자동화",
    "멀티모달 AI":        "#멀티모달 #AI",
    "AI 코딩 개발":       "#AIcoding #개발 #AI",
    "default":            "#AI #인공지능 #LLM",
}


def _split_to_tweet(text: str, max_len: int = TWEET_MAX) -> list:
    """텍스트를 280자 단위로 자연스럽게 분할"""
    if len(text) <= max_len:
        return [text]

    tweets = []
    sentences = text.replace('. ', '.\n').replace('다. ', '다.\n').split('\n')
    current = ''
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        test = (current + ' ' + sentence).strip() if current else sentence
        if len(test) <= max_len:
            current = test
        else:
            if current:
                tweets.append(current)
            if len(sentence) > max_len:
                chunks = textwrap.wrap(sentence, max_len - 5)
                tweets.extend(chunks[:-1])
                current = chunks[-1] if chunks else ''
            else:
                current = sentence
    if current:
        tweets.append(current)
    return tweets or [text[:max_len]]


def convert(article: dict, blog_url: str = '', save_file: bool = True) -> list:
    """
    article dict → X 스레드 트윗 리스트.
    각 트윗: {'order': int, 'text': str, 'char_count': int}
    Returns: 트윗 리스트
    """
    title = article.get('title', '')
    corner = article.get('corner', '')
    domain = article.get('domain', '')
    key_points = article.get('key_points', [])
    tags = article.get('tags', [])
    slug = article.get('slug', 'article')

    logger.info(f"스레드 변환 시작: {title}")

    # 도메인 → 해시태그 (corner 우선, 없으면 domain, 없으면 default)
    hashtags = DOMAIN_HASHTAGS.get(domain, DOMAIN_HASHTAGS.get(corner, DOMAIN_HASHTAGS['default']))
    tag_str = ' '.join(f'#{t}' for t in tags[:3] if t)
    if tag_str:
        hashtags = hashtags + ' ' + tag_str

    tweets = []

    # 트윗 1: 흥미 유발 + 제목 + 해시태그
    intro_text = f"👀 {title}\n\n{hashtags} {BRAND_TAG}"
    if len(intro_text) <= TWEET_MAX:
        tweets.append(intro_text)
    else:
        short_title = textwrap.shorten(title, width=100, placeholder='...')
        tweets.append(f"👀 {short_title}\n\n{hashtags}")

    # 트윗 2-4: 핵심 포인트
    for i, point in enumerate(key_points[:3], 1):
        bullets = ['①', '②', '③']
        bullet = bullets[i - 1] if i <= 3 else f'{i}.'
        tweet_text = f"{bullet} {point}"
        if len(tweet_text) <= TWEET_MAX:
            tweets.append(tweet_text)
        else:
            split_tweets = _split_to_tweet(tweet_text)
            tweets.extend(split_tweets)

    # 마지막 트윗: CTA + 블로그 링크
    post_url = blog_url or f"{BLOG_BASE_URL.rstrip('/')}/search/label/{slug}"
    cta_text = f"전체 내용 보기 👇\n{post_url}\n\n{BRAND_TAG}"
    tweets.append(cta_text)

    result = [
        {'order': i + 1, 'text': t, 'char_count': len(t)}
        for i, t in enumerate(tweets)
    ]

    if save_file:
        date_str = datetime.now().strftime('%Y%m%d')
        filename = f"{date_str}_{slug}_thread.json"
        output_path = OUTPUT_DIR / filename
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8'
        )
        logger.info(f"스레드 저장: {output_path} ({len(result)}개 트윗)")

    logger.info("스레드 변환 완료")
    return result


if __name__ == '__main__':
    sample = {
        'title': 'ChatGPT o3 완벽 분석: 2025년 가장 강력한 AI 모델',
        'slug': 'chatgpt-o3-analysis',
        'domain': 'ChatGPT OpenAI',
        'corner': 'AI 소식',
        'tags': ['ChatGPT', 'OpenAI', 'AI'],
        'key_points': [
            'o3는 수학·코딩에서 인간 전문가 수준 달성',
            'API 비용이 GPT-4o 대비 6배 높음',
            '멀티모달 지원으로 이미지 분석도 가능',
        ],
    }
    threads = convert(sample)
    for t in threads:
        print(f"[{t['order']}] ({t['char_count']}자) {t['text']}")
        print()
