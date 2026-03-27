"""
SNS Pipeline Agent — P004 (agents/sns_pipeline.py)
블로그 포스트 → 5개 SNS 포맷 변환 + 배포
blog-writer(sinmb79/blog-writer) 아키텍처 기반

파이프라인 (포스트 1개당):
  1. article dict 변환 (post_meta_to_article)
  2. 카드 이미지 생성 (card_converter) — Pillow 필요
  3. X 스레드 JSON 생성 (thread_converter)
  4. 뉴스레터 아이템 수집 (newsletter_converter)
  5. Instagram 게시 (INSTAGRAM_ACCESS_TOKEN 있을 때)
  6. X 스레드 게시 (X_API_KEY 있을 때)
  7. YouTube 쇼츠 (ffmpeg + shorts_converter)
"""
import os
import sys
import json
import datetime
import traceback
from pathlib import Path

BASE = Path(__file__).parent.parent
TODAY = datetime.date.today().isoformat()

# 경로 설정
sys.path.insert(0, str(BASE))

OUT_THREADS     = BASE / 'output' / 'threads'
OUT_IMAGES      = BASE / 'output' / 'images'
OUT_NEWSLETTERS = BASE / 'output' / 'newsletters'
OUT_SHORTS      = BASE / 'output' / 'shorts'
OUT_POSTS       = BASE / 'output' / 'posts'
OUT_LOGS        = BASE / 'output' / 'logs'

for d in [OUT_THREADS, OUT_IMAGES, OUT_NEWSLETTERS, OUT_SHORTS, OUT_LOGS]:
    d.mkdir(parents=True, exist_ok=True)

import logging
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.FileHandler(OUT_LOGS / f'sns_pipeline_{TODAY}.log', encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)


def _load_converters():
    """컨버터 모듈 임포트 (실패 시 None)"""
    converters = {}
    try:
        from agents.converters.article_adapter import post_meta_to_article
        converters['adapter'] = post_meta_to_article
    except Exception as e:
        logger.warning(f"article_adapter 임포트 실패: {e}")

    try:
        from agents.converters import card_converter
        converters['card'] = card_converter
    except Exception as e:
        logger.warning(f"card_converter 임포트 실패: {e}")

    try:
        from agents.converters import thread_converter
        converters['thread'] = thread_converter
    except Exception as e:
        logger.warning(f"thread_converter 임포트 실패: {e}")

    try:
        from agents.converters import newsletter_converter
        converters['newsletter'] = newsletter_converter
    except Exception as e:
        logger.warning(f"newsletter_converter 임포트 실패: {e}")

    try:
        from agents.converters import shorts_converter
        converters['shorts'] = shorts_converter
    except Exception as e:
        logger.warning(f"shorts_converter 임포트 실패: {e}")

    return converters


def _load_distributors():
    """배포 모듈 임포트 (실패 시 None)"""
    distributors = {}

    try:
        from agents.distributors import instagram_bot
        distributors['instagram'] = instagram_bot
    except Exception as e:
        logger.warning(f"instagram_bot 임포트 실패: {e}")

    try:
        from agents.distributors import x_bot
        distributors['x'] = x_bot
    except Exception as e:
        logger.warning(f"x_bot 임포트 실패: {e}")

    try:
        from agents.distributors import youtube_bot
        distributors['youtube'] = youtube_bot
    except Exception as e:
        logger.warning(f"youtube_bot 임포트 실패: {e}")

    return distributors


def _extract_key_points_from_html(html: str, seo_plan: dict) -> list:
    """HTML 본문 또는 SEO 계획에서 핵심 포인트 3개 추출"""
    import re

    # 방법 1: SEO 계획 outline에서 추출
    plan = seo_plan.get("plan", seo_plan)  # seo_plan이 직접 plan인 경우도 처리
    outline = plan.get("outline", [])
    points = []
    for sec in outline[:3]:
        kps = sec.get("key_points", [])
        if kps:
            clean = re.sub(r'<[^>]+>', '', str(kps[0])).strip()[:40]
            if clean:
                points.append(clean)

    # 방법 2: h2 태그에서 추출 (outline 없으면)
    if not points and html:
        h2_matches = re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.IGNORECASE)
        points = [re.sub(r'<[^>]+>', '', h).strip()[:40] for h in h2_matches[:3] if h.strip()]

    return points[:3]


def _load_html_for_post(post_meta: dict) -> str:
    """post_meta에서 html_file 경로를 찾아 내용 로드"""
    html_file = post_meta.get('html_file', '')
    if not html_file:
        return ''
    html_path = OUT_POSTS / html_file
    if html_path.exists():
        try:
            return html_path.read_text(encoding='utf-8')
        except Exception:
            return ''
    return ''


def run(write_data: dict = None, image_data: dict = None) -> dict:
    """
    SNS 파이프라인 메인 함수.

    Args:
        write_data: writer.py 출력 {'date': ..., 'posts': [...]}
        image_data: image_gen.py 출력 {'posts': [{'post_num': ..., 'card': ..., 'thumbnail': ...}]}

    Returns:
        {
            "date": TODAY,
            "results": [
                {
                    "post_num": 1,
                    "title": "...",
                    "formats": {
                        "card": "output/images/...png" or None,
                        "thread": "output/threads/...json" or None,
                        "shorts": "output/shorts/...mp4" or None,
                        "newsletter": True/False,
                    },
                    "distributed": {
                        "instagram": True/False,
                        "x_thread": True/False,
                        "youtube": True/False,
                    }
                }
            ],
            "newsletter_html": "output/newsletters/weekly_...html" or None,
        }
    """
    logger.info(f"[SNS Pipeline] 시작 — {TODAY}")

    if write_data is None:
        # 오늘 write_log 파일 로드 시도
        write_log = OUT_POSTS / f"write_log_{TODAY}.json"
        if write_log.exists():
            try:
                write_data = json.loads(write_log.read_text(encoding='utf-8'))
                logger.info(f"write_data 로드: {write_log}")
            except Exception as e:
                logger.error(f"write_data 로드 실패: {e}")
                write_data = {'date': TODAY, 'posts': []}
        else:
            logger.warning("write_data 없음 — SNS 파이프라인 건너뜀")
            return {'date': TODAY, 'results': [], 'newsletter_html': None}

    posts = write_data.get('posts', [])
    if not posts:
        logger.warning("포스트 없음 — SNS 파이프라인 종료")
        return {'date': TODAY, 'results': [], 'newsletter_html': None}

    # image_data 인덱싱 (post_num → 이미지 경로)
    image_map = {}
    if image_data:
        for img_post in image_data.get('posts', []):
            pnum = img_post.get('post_num', 0)
            image_map[pnum] = {
                'card': img_post.get('card', ''),
                'thumbnail': img_post.get('thumbnail', ''),
            }

    # 모듈 로드
    converters = _load_converters()
    distributors = _load_distributors()

    results = []
    newsletter_articles = []
    newsletter_urls = []

    for post_meta in posts:
        post_num = post_meta.get('post_num', 1)
        title = post_meta.get('title', '')
        logger.info(f"\n[{post_num}] {title[:60]}")

        result = {
            'post_num': post_num,
            'title': title,
            'formats': {'card': None, 'thread': None, 'shorts': None, 'newsletter': False},
            'distributed': {'instagram': False, 'x_thread': False, 'youtube': False},
        }

        # key_points 없으면 HTML에서 추출
        if not post_meta.get('key_points'):
            html = _load_html_for_post(post_meta)
            key_points = _extract_key_points_from_html(html, {})
            if key_points:
                post_meta['key_points'] = key_points
                logger.info(f"  key_points 추출 완료: {key_points}")
            else:
                post_meta['key_points'] = []

        # article dict 변환
        html_content = _load_html_for_post(post_meta)
        if 'adapter' in converters:
            try:
                article = converters['adapter'](post_meta, html_content)
            except Exception as e:
                logger.error(f"  article 변환 실패: {e}")
                article = {
                    'title': title,
                    'meta': post_meta.get('meta_description', ''),
                    'slug': post_meta.get('slug', ''),
                    'tags': post_meta.get('labels', [])[:5],
                    'corner': 'AI 인사이트',
                    'key_points': post_meta.get('key_points', []),
                    'sources': [],
                    'body': html_content,
                    'domain': post_meta.get('domain', ''),
                    'primary_keyword': post_meta.get('primary_keyword', ''),
                }
        else:
            article = {'title': title, 'slug': post_meta.get('slug', ''), 'corner': 'AI 인사이트',
                       'key_points': post_meta.get('key_points', []), 'tags': post_meta.get('labels', [])[:5]}

        # ── 포맷 변환 ─────────────────────────────────

        # 1. 카드 이미지 (image_gen에서 생성한 것 있으면 재사용, 없으면 card_converter)
        existing_card = image_map.get(post_num, {}).get('card', '')
        if existing_card and Path(existing_card).exists():
            result['formats']['card'] = existing_card
            logger.info(f"  ✅ 카드 이미지 재사용: {Path(existing_card).name}")
        elif 'card' in converters:
            try:
                card_path = converters['card'].convert(article, save_file=True)
                if card_path:
                    result['formats']['card'] = card_path
                    logger.info(f"  ✅ 카드 이미지 생성: {Path(card_path).name}")
                else:
                    logger.warning("  ⚠ 카드 이미지 생성 실패 (Pillow 미설치?)")
            except Exception as e:
                logger.warning(f"  ⚠ 카드 변환 오류: {e}")
        else:
            logger.info("  ℹ 카드 컨버터 없음 — 건너뜀")

        # 2. X 스레드 JSON
        if 'thread' in converters:
            try:
                blog_url = post_meta.get('url', '')
                thread_data = converters['thread'].convert(article, blog_url=blog_url, save_file=True)
                # 저장된 파일 경로 반환
                slug = article.get('slug', 'article')
                thread_file = OUT_THREADS / f"{datetime.date.today().strftime('%Y%m%d')}_{slug}_thread.json"
                if thread_file.exists():
                    result['formats']['thread'] = str(thread_file)
                    logger.info(f"  ✅ 스레드 JSON 생성: {thread_file.name} ({len(thread_data)}개 트윗)")
                else:
                    result['formats']['thread'] = None
                    logger.warning("  ⚠ 스레드 파일 미생성")
            except Exception as e:
                logger.warning(f"  ⚠ 스레드 변환 오류: {e}")
                traceback.print_exc()
        else:
            logger.info("  ℹ 스레드 컨버터 없음 — 건너뜀")

        # 3. 뉴스레터 아이템 수집
        if 'newsletter' in converters:
            try:
                blog_url = post_meta.get('url', '')
                item = converters['newsletter'].extract_newsletter_item(article, blog_url)
                newsletter_articles.append(article)
                newsletter_urls.append(blog_url)
                result['formats']['newsletter'] = True
                logger.info(f"  ✅ 뉴스레터 아이템 수집")
            except Exception as e:
                logger.warning(f"  ⚠ 뉴스레터 수집 오류: {e}")
        else:
            logger.info("  ℹ 뉴스레터 컨버터 없음 — 건너뜀")

        # 4. 쇼츠 변환 (ffmpeg 있을 때만)
        if 'shorts' in converters:
            try:
                shorts_path = converters['shorts'].convert(article, save_file=True)
                if shorts_path:
                    result['formats']['shorts'] = shorts_path
                    logger.info(f"  ✅ 쇼츠 생성: {Path(shorts_path).name}")
                else:
                    result['formats']['shorts'] = None
                    logger.info("  ℹ 쇼츠 생성 건너뜀 (ffmpeg 없음 또는 key_points 없음)")
            except Exception as e:
                logger.info(f"  ℹ 쇼츠 생성 건너뜀: {e}")
        else:
            logger.info("  ℹ 쇼츠 컨버터 없음 — 건너뜀")

        # ── 배포 ──────────────────────────────────────

        # 5. Instagram (자격증명 있을 때만)
        if 'instagram' in distributors:
            try:
                card_path = result['formats'].get('card') or ''
                if card_path:
                    ok = distributors['instagram'].publish_card(article, card_path)
                    result['distributed']['instagram'] = ok
                    logger.info(f"  {'✅' if ok else '⚠'} Instagram: {'발행 성공' if ok else '건너뜀'}")
                else:
                    logger.info("  ℹ Instagram: 카드 이미지 없음 — 건너뜀")
            except Exception as e:
                logger.warning(f"  ⚠ Instagram 오류: {e}")

        # 6. X 스레드 (자격증명 있을 때만)
        if 'x' in distributors and result['formats'].get('thread'):
            try:
                thread_file = result['formats']['thread']
                ok = distributors['x'].publish_thread_from_file(article, thread_file)
                result['distributed']['x_thread'] = ok
                logger.info(f"  {'✅' if ok else '⚠'} X 스레드: {'발행 성공' if ok else '건너뜀'}")
            except Exception as e:
                logger.warning(f"  ⚠ X 스레드 오류: {e}")

        # 7. YouTube 쇼츠 (token.json + 영상 있을 때만)
        if 'youtube' in distributors and result['formats'].get('shorts'):
            try:
                ok = distributors['youtube'].publish_shorts(article, result['formats']['shorts'])
                result['distributed']['youtube'] = ok
                logger.info(f"  {'✅' if ok else '⚠'} YouTube: {'발행 성공' if ok else '건너뜀'}")
            except Exception as e:
                logger.warning(f"  ⚠ YouTube 오류: {e}")

        results.append(result)

    # ── 주간 뉴스레터 HTML 생성 ─────────────────────────
    newsletter_html_path = None
    if newsletter_articles and 'newsletter' in converters:
        try:
            html = converters['newsletter'].generate_weekly(
                newsletter_articles, newsletter_urls, save_file=True
            )
            date_str = datetime.date.today().strftime('%Y%m%d')
            newsletter_html_path = str(OUT_NEWSLETTERS / f"weekly_{date_str}_newsletter.html")
            logger.info(f"뉴스레터 HTML 생성: {newsletter_html_path}")
        except Exception as e:
            logger.warning(f"뉴스레터 HTML 생성 오류: {e}")

    # ── 결과 저장 ─────────────────────────────────────
    final_result = {
        'date': TODAY,
        'results': results,
        'newsletter_html': newsletter_html_path,
    }

    log_path = OUT_LOGS / f'sns_pipeline_result_{TODAY}.json'
    log_path.write_text(
        json.dumps(final_result, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )

    # 요약 출력
    logger.info(f"\n[SNS Pipeline] 완료 — {len(results)}개 포스트 처리")
    for r in results:
        fmts = r['formats']
        dist = r['distributed']
        fmt_str = ', '.join(k for k, v in fmts.items() if v)
        dist_str = ', '.join(k for k, v in dist.items() if v) or '없음'
        logger.info(f"  [{r['post_num']}] {r['title'][:40]}")
        logger.info(f"      포맷: {fmt_str or '없음'} | 배포: {dist_str}")

    return final_result


if __name__ == '__main__':
    # 드라이런 (더미 데이터)
    today = datetime.date.today().isoformat()
    dummy_write = {
        'date': today,
        'posts': [
            {
                'post_num': 1,
                'title': 'ChatGPT o3 완벽 분석: 2025년 가장 강력한 AI 모델의 실력은?',
                'slug': 'chatgpt-o3-analysis',
                'primary_keyword': 'ChatGPT o3',
                'secondary_keywords': ['OpenAI', 'AI 모델', 'GPT-4'],
                'meta_description': 'ChatGPT o3의 성능, 비용, 활용법을 완벽 분석합니다.',
                'domain': 'ChatGPT OpenAI',
                'labels': ['ChatGPT', 'OpenAI', 'AI', '인공지능'],
                'char_count': 4200,
                'key_points': [
                    'o3는 수학·코딩에서 인간 전문가 수준 달성',
                    'API 비용이 GPT-4o 대비 6배 높음',
                    '멀티모달 지원으로 이미지 분석도 가능',
                ],
                'html_file': f'post_{today}_1.html',
            }
        ]
    }
    result = run(dummy_write)
    print(json.dumps(result, ensure_ascii=False, indent=2))
