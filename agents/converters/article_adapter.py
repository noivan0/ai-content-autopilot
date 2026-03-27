"""
article_adapter.py — P004 post_meta → blog-writer article dict 변환 헬퍼
(agents/converters/article_adapter.py)

blog-writer 컨버터들은 article dict를 받아 처리한다.
P004의 post_meta (writer.py 출력 형태)를 article dict로 변환한다.
"""
from typing import Optional


# domain → corner (SNS 배지) 매핑
DOMAIN_TO_CORNER = {
    "ChatGPT OpenAI":     "AI 소식",
    "Claude Anthropic":   "AI 소식",
    "Gemini Google AI":   "AI 소식",
    "Manus AI 에이전트":  "AI 소식",
    "LLM 언어모델":       "AI 분석",
    "AI 에이전트 자동화": "AI 활용",
    "멀티모달 AI":        "AI 활용",
    "AI 코딩 개발":       "AI 개발",
    "default":            "AI 인사이트",
}


def post_meta_to_article(post_meta: dict, html_content: str = '') -> dict:
    """
    P004 post_meta (writer.py 출력 or meta JSON) → blog-writer article dict 변환.

    post_meta 구조 (writer.py 반환):
        title, slug, primary_keyword, secondary_keywords,
        meta_description, domain, labels, char_count,
        key_points (있으면), html_file, ...

    article dict 구조 (blog-writer 컨버터 입력):
        title, meta, slug, tags, corner, key_points,
        sources, body, domain, primary_keyword
    """
    domain = post_meta.get('domain', '')
    corner = DOMAIN_TO_CORNER.get(domain, DOMAIN_TO_CORNER['default'])

    # key_points 처리: 없거나 빈 리스트면 빈 리스트 (sns_pipeline에서 채움)
    key_points = post_meta.get('key_points', [])
    if not isinstance(key_points, list):
        key_points = []

    # tags: labels 중 유의미한 것 5개
    labels = post_meta.get('labels', [])
    tags = [str(lbl) for lbl in labels if lbl][:5]

    # sources: secondary_keywords → source 형태로
    secondary_kws = post_meta.get('secondary_keywords', [])
    sources = [{'title': kw, 'url': ''} for kw in secondary_kws[:3] if kw]

    return {
        'title':           post_meta.get('title', ''),
        'meta':            post_meta.get('meta_description', ''),
        'slug':            post_meta.get('slug', ''),
        'tags':            tags,
        'corner':          corner,
        'key_points':      key_points,
        'sources':         sources,
        'body':            html_content,
        'domain':          domain,
        'primary_keyword': post_meta.get('primary_keyword', ''),
    }


def article_to_post_meta(article: dict) -> dict:
    """역변환: article dict → post_meta (필요 시 사용)"""
    return {
        'title':              article.get('title', ''),
        'meta_description':   article.get('meta', ''),
        'slug':               article.get('slug', ''),
        'labels':             article.get('tags', []),
        'domain':             article.get('domain', ''),
        'primary_keyword':    article.get('primary_keyword', ''),
        'key_points':         article.get('key_points', []),
        'secondary_keywords': [s['title'] for s in article.get('sources', [])],
    }
