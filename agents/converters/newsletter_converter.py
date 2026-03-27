"""
뉴스레터 변환봇 — P004 버전 (agents/converters/newsletter_converter.py)
역할: article dict → 주간 뉴스레터 HTML
출력: output/newsletters/weekly_{date}_newsletter.html

ref: sinmb79/blog-writer bots/converters/newsletter_converter.py
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
LOG_DIR = BASE_DIR / 'output' / 'logs'
OUTPUT_DIR = BASE_DIR / 'output' / 'newsletters'
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

# 코너 색상 (뉴스레터 배지)
CORNER_COLORS = {
    'AI 소식':   '#3b82f6',
    'AI 분석':   '#7c3aed',
    'AI 활용':   '#10a37f',
    'AI 개발':   '#84cc16',
    'AI 인사이트': '#f59e0b',
}


def extract_newsletter_item(article: dict, blog_url: str = '') -> dict:
    """단일 글에서 뉴스레터용 발췌 추출"""
    slug = article.get('slug', '')
    return {
        'title': article.get('title', ''),
        'meta': article.get('meta', article.get('meta_description', '')),
        'corner': article.get('corner', ''),
        'key_points': article.get('key_points', []),
        'primary_keyword': article.get('primary_keyword', ''),
        'url': blog_url or f"{BLOG_BASE_URL.rstrip('/')}/search/label/{slug}",
        'extracted_at': datetime.now().isoformat(),
    }


def build_newsletter_html(items: list, week_str: str = '') -> str:
    """주간 뉴스레터 HTML 생성"""
    if not week_str:
        week_str = datetime.now().strftime('%Y년 %m월 %d일 주간')

    article_blocks = []
    for item in items:
        corner = item.get('corner', 'AI 인사이트')
        corner_color = CORNER_COLORS.get(corner, '#3b82f6')
        points_html = ''.join(
            f'<li style="margin-bottom:4px;">{p}</li>' for p in item.get('key_points', [])
        )
        block = f"""
        <div style="margin-bottom:32px;padding-bottom:24px;border-bottom:1px solid #eee;">
          <p style="color:{corner_color};font-size:12px;font-weight:bold;margin:0 0 4px;text-transform:uppercase;">{corner}</p>
          <h2 style="font-size:20px;margin:0 0 8px;line-height:1.4;">
            <a href="{item.get('url','')}" style="color:#1a1a1a;text-decoration:none;">{item.get('title','')}</a>
          </h2>
          <p style="color:#555;font-size:14px;margin:0 0 12px;line-height:1.6;">{item.get('meta','')}</p>
          <ul style="color:#333;font-size:14px;margin:0;padding-left:20px;line-height:1.7;">
            {points_html}
          </ul>
          <p style="margin:12px 0 0;">
            <a href="{item.get('url','')}" style="color:{corner_color};font-size:13px;font-weight:bold;">전체 읽기 →</a>
          </p>
        </div>"""
        article_blocks.append(block)

    articles_html = '\n'.join(article_blocks)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI 인사이트 주간 뉴스레터 — {week_str}</title>
</head>
<body style="font-family:'Noto Sans KR','Apple SD Gothic Neo',sans-serif;max-width:600px;margin:0 auto;padding:20px;color:#1a1a1a;background:#fafafa;">
  <div style="background:linear-gradient(135deg,#3b82f6,#1d4ed8);padding:28px 24px;margin-bottom:32px;border-radius:8px;">
    <h1 style="color:#fff;margin:0 0 4px;font-size:28px;font-weight:900;">AI 인사이트</h1>
    <p style="color:rgba(255,255,255,0.85);margin:0;font-size:14px;">{week_str} 뉴스레터 · P004 자동 생성</p>
  </div>

  <div style="background:#fff;padding:24px;border-radius:8px;border:1px solid #e5e7eb;">
    {articles_html}
  </div>

  <div style="margin-top:24px;padding:16px;text-align:center;background:#fff;border-radius:8px;border:1px solid #e5e7eb;">
    <p style="color:#6b7280;font-size:12px;margin:0;">
      <a href="{BLOG_BASE_URL}" style="color:#3b82f6;text-decoration:none;font-weight:bold;">ai-insight-blog.blogspot.com</a>
      &nbsp;·&nbsp; by P004 Auto Pipeline
      &nbsp;·&nbsp; {datetime.now().strftime('%Y-%m-%d')}
    </p>
  </div>
</body>
</html>"""


def generate_weekly(articles: list, urls: list = None, save_file: bool = True) -> str:
    """
    여러 글을 모아 주간 뉴스레터 HTML 생성.
    articles: article dict 리스트
    urls: 각 글의 발행 URL (없으면 slug로 생성)
    Returns: HTML 문자열
    """
    logger.info(f"주간 뉴스레터 생성 시작: {len(articles)}개 글")

    items = []
    for i, article in enumerate(articles):
        url = (urls[i] if urls and i < len(urls) else '')
        items.append(extract_newsletter_item(article, url))

    week_str = datetime.now().strftime('%Y년 %m월 %d일')
    html = build_newsletter_html(items, week_str)

    if save_file:
        date_str = datetime.now().strftime('%Y%m%d')
        filename = f"weekly_{date_str}_newsletter.html"
        output_path = OUTPUT_DIR / filename
        output_path.write_text(html, encoding='utf-8')
        logger.info(f"뉴스레터 저장: {output_path}")

    logger.info("주간 뉴스레터 생성 완료")
    return html


if __name__ == '__main__':
    samples = [
        {
            'title': 'ChatGPT o3 완벽 분석: 2025년 가장 강력한 AI 모델',
            'meta': 'ChatGPT o3의 성능, 비용, 활용법을 완벽 분석합니다.',
            'slug': 'chatgpt-o3-analysis',
            'corner': 'AI 소식',
            'key_points': [
                'o3는 수학·코딩에서 인간 전문가 수준 달성',
                'API 비용이 GPT-4o 대비 6배 높음',
                '멀티모달 지원으로 이미지 분석도 가능',
            ],
        },
    ]
    html = generate_weekly(samples)
    print(html[:500])
