"""
카드 변환봇 — P004 버전 (agents/converters/card_converter.py)
역할: article dict → 인스타그램 카드 이미지 PNG
- 크기: 1080×1080 (정사각형)
- 배경: 흰색 + AI 블루 액센트 (#3b82f6)
- 폰트: Noto Sans KR (없으면 시스템 폰트 폴백)
- 구성: 로고 + 코너 배지 + 제목 + 핵심 3줄 + URL

ref: sinmb79/blog-writer bots/converters/card_converter.py
"""
import logging
import textwrap
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
LOG_DIR = BASE_DIR / 'output' / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = BASE_DIR / 'output' / 'images'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR = BASE_DIR / 'assets'
FONTS_DIR = ASSETS_DIR / 'fonts'

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.FileHandler(LOG_DIR / 'converter.log', encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)

# ── 디자인 상수 ────────────────────────────────────────────────
CARD_SIZE = (1080, 1080)
COLOR_WHITE = (255, 255, 255)
COLOR_BLUE = (59, 130, 246)        # #3b82f6 — P004 AI 인사이트 기본 색
COLOR_DARK = (30, 30, 30)
COLOR_GRAY = (120, 120, 120)
COLOR_BLUE_LIGHT = (239, 246, 255)

# 코너(도메인) 색상
CORNER_COLORS = {
    'AI 소식':   (59, 130, 246),    # 파랑
    'AI 분석':   (124, 58, 237),    # 보라
    'AI 활용':   (16, 163, 127),    # 초록
    'AI 개발':   (132, 204, 22),    # 라임
    'AI 인사이트': (245, 158, 11),  # 황금
}

BLOG_URL = 'ai-insight-blog.blogspot.com'  # placeholder — BLOG_URL env로 덮어씀
BRAND_NAME = 'AI 인사이트'
SUB_BRAND = 'by P004'

import os
_env_blog_url = os.environ.get('BLOG_URL', '')
if _env_blog_url:
    BLOG_URL = _env_blog_url.replace('https://', '').replace('http://', '').rstrip('/')


def _load_font(size: int):
    """Noto Sans KR → 시스템 폰트 → 기본 폰트 폴백"""
    try:
        from PIL import ImageFont
        # P004 assets/fonts/ 우선
        for fname in ['NotoSansKR-Bold.ttf', 'NotoSansKR-Regular.ttf', 'NotoSansKR-Medium.ttf']:
            font_path = FONTS_DIR / fname
            if font_path.exists():
                return ImageFont.truetype(str(font_path), size)
        # 시스템 한글 폰트 (Linux → Mac → Windows 순서)
        for path in [
            '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            '/System/Library/Fonts/AppleSDGothicNeo.ttc',
            'C:/Windows/Fonts/malgun.ttf',
            'C:/Windows/Fonts/malgunbd.ttf',
            'C:/Windows/Fonts/NanumGothic.ttf',
        ]:
            if Path(path).exists():
                return ImageFont.truetype(path, size)
        return ImageFont.load_default()
    except Exception:
        return None


def _draw_rounded_rect(draw, xy, radius: int, fill):
    """PIL로 둥근 사각형 그리기"""
    x1, y1, x2, y2 = xy
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
    draw.ellipse([x1, y1, x1 + radius * 2, y1 + radius * 2], fill=fill)
    draw.ellipse([x2 - radius * 2, y1, x2, y1 + radius * 2], fill=fill)
    draw.ellipse([x1, y2 - radius * 2, x1 + radius * 2, y2], fill=fill)
    draw.ellipse([x2 - radius * 2, y2 - radius * 2, x2, y2], fill=fill)


def convert(article: dict, save_file: bool = True) -> str:
    """
    article dict → 카드 이미지 PNG.
    Returns: 저장 경로 문자열 (save_file=False면 빈 문자열)
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        logger.error("Pillow 미설치. pip install Pillow")
        return ''

    title = article.get('title', '')
    corner = article.get('corner', 'AI 인사이트')
    key_points = article.get('key_points', [])

    logger.info(f"카드 변환 시작: {title}")

    # 캔버스
    img = Image.new('RGB', CARD_SIZE, COLOR_WHITE)
    draw = ImageDraw.Draw(img)

    # 상단 바 (80px)
    draw.rectangle([0, 0, 1080, 80], fill=COLOR_BLUE)

    # 폰트 로드
    font_brand  = _load_font(36)
    font_sub    = _load_font(22)
    font_corner = _load_font(26)
    font_title  = _load_font(52)
    font_point  = _load_font(38)
    font_url    = _load_font(28)

    # 브랜드명 (좌상단)
    if font_brand:
        draw.text((40, 22), BRAND_NAME, font=font_brand, fill=COLOR_WHITE)
    if font_sub:
        draw.text((460, 28), SUB_BRAND, font=font_sub, fill=(200, 220, 255))

    # 코너 배지
    badge_color = CORNER_COLORS.get(corner, COLOR_BLUE)
    _draw_rounded_rect(draw, [40, 110, 280, 160], 20, badge_color)
    if font_corner:
        draw.text((60, 122), corner, font=font_corner, fill=COLOR_WHITE)

    # 제목 (멀티라인, 최대 3줄)
    title_lines = textwrap.wrap(title, width=18)[:3]
    y_title = 200
    for line in title_lines:
        if font_title:
            draw.text((40, y_title), line, font=font_title, fill=COLOR_DARK)
        y_title += 65

    # 구분선
    draw.rectangle([40, y_title + 10, 1040, y_title + 14], fill=COLOR_BLUE)

    # 핵심 포인트
    y_points = y_title + 40
    for i, point in enumerate(key_points[:3]):
        draw.ellipse([40, y_points + 8, 64, y_points + 32], fill=COLOR_BLUE)
        if font_point:
            point_short = textwrap.shorten(str(point), width=22, placeholder='...')
            draw.text((76, y_points), point_short, font=font_point, fill=COLOR_DARK)
        y_points += 60

    # 하단 바 (URL + 브랜딩)
    draw.rectangle([0, 980, 1080, 1080], fill=COLOR_BLUE)
    if font_url:
        draw.text((40, 1008), BLOG_URL, font=font_url, fill=COLOR_WHITE)

    # 저장
    output_path = ''
    if save_file:
        slug = article.get('slug', 'article')
        date_str = datetime.now().strftime('%Y%m%d')
        filename = f"{date_str}_{slug}_card.png"
        output_path = str(OUTPUT_DIR / filename)
        img.save(output_path, 'PNG')
        logger.info(f"카드 저장: {output_path}")

    logger.info("카드 변환 완료")
    return output_path


if __name__ == '__main__':
    sample = {
        'title': 'ChatGPT o3 완벽 분석: 2025년 가장 강력한 AI 모델',
        'slug': 'chatgpt-o3-analysis',
        'corner': 'AI 소식',
        'key_points': [
            'o3는 수학·코딩에서 인간 전문가 수준 달성',
            'API 비용이 GPT-4o 대비 6배 높음',
            '멀티모달 지원으로 이미지 분석도 가능',
        ],
    }
    path = convert(sample)
    print(f"저장: {path}")
