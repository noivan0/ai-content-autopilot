"""
P004 — 이미지 생성 에이전트
blog-writer 카드 기술 적용:
  - 썸네일 1200×630 (블로그 OG 이미지)
  - 인스타그램 카드 1080×1080 (금색 상단/하단 바)
  - ImgBB 업로드 (IMGBB_API_KEY 환경변수)
  - HTML figure 태그 자리 교체
"""
import os, sys, json, re, base64, datetime
from pathlib import Path

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_OK = True
except ImportError:
    PIL_OK = False
    print("[image_gen] ⚠ Pillow 미설치 — pip install Pillow")

try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

TODAY = datetime.date.today().isoformat()

# ─── 도메인별 배지 색상 ────────────────────────────────────────────────────────
DOMAIN_COLORS = {
    "ChatGPT OpenAI":   "#10a37f",   # OpenAI 그린
    "Claude Anthropic": "#c97f4a",   # Anthropic 오렌지
    "Gemini Google AI": "#4285f4",   # Google 블루
    "Manus AI 에이전트": "#7c3aed",  # 퍼플
    "LLM 언어모델":     "#ef4444",   # 레드
    "AI 에이전트 자동화": "#f59e0b", # 앰버
    "멀티모달 AI":      "#06b6d4",   # 사이언
    "AI 코딩 개발":     "#84cc16",   # 라임
    "default":          "#3b82f6",   # 기본 블루
}

# ─── 폰트 경로 우선순위 ───────────────────────────────────────────────────────
FONT_PATHS = [
    os.path.join(BASE, "assets/fonts/NotoSansKR-Bold.ttf"),
    os.path.join(BASE, "assets/fonts/NotoSansKR-Regular.ttf"),
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKkr-Regular.otf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


# ─── 유틸리티 ─────────────────────────────────────────────────────────────────

def hex_to_rgb(hex_color: str) -> tuple:
    """#rrggbb → (r, g, b)"""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def load_font(size: int, bold: bool = False) -> "ImageFont.FreeTypeFont":
    """사용 가능한 폰트 로드 (폴백 체인)"""
    if not PIL_OK:
        return None
    for path in FONT_PATHS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def wrap_text(text: str, font, max_width: int, draw: "ImageDraw.Draw") -> list:
    """한글/영문 혼합 텍스트 자동 줄바꿈 (단어 단위)"""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        try:
            bbox = draw.textbbox((0, 0), test, font=font)
            w = bbox[2] - bbox[0]
        except Exception:
            w = len(test) * (font.size if hasattr(font, "size") else 12)
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def wrap_text_chars(text: str, font, max_width: int, draw: "ImageDraw.Draw") -> list:
    """글자 단위 줄바꿈 (한글은 단어 경계가 없어 보조로 사용)"""
    if not text:
        return []
    lines = []
    current = ""
    for char in text:
        test = current + char
        try:
            bbox = draw.textbbox((0, 0), test, font=font)
            w = bbox[2] - bbox[0]
        except Exception:
            w = len(test) * 12
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines


def smart_wrap(text: str, font, max_width: int, draw: "ImageDraw.Draw", max_lines: int = 3) -> list:
    """단어 우선, 글자 보완 줄바꿈 + 최대 줄 수 제한"""
    # 먼저 단어 단위로 시도
    lines = wrap_text(text, font, max_width, draw)
    if len(lines) <= max_lines:
        return lines[:max_lines]
    # 단어 단위로 너무 많으면 글자 단위로 재시도
    lines = wrap_text_chars(text, font, max_width, draw)
    return lines[:max_lines]


def draw_rounded_rect(draw: "ImageDraw.Draw", xy: tuple, radius: int, fill: tuple, outline: tuple = None):
    """둥근 모서리 사각형 그리기"""
    x1, y1, x2, y2 = xy
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
    draw.ellipse([x1, y1, x1 + 2*radius, y1 + 2*radius], fill=fill)
    draw.ellipse([x2 - 2*radius, y1, x2, y1 + 2*radius], fill=fill)
    draw.ellipse([x1, y2 - 2*radius, x1 + 2*radius, y2], fill=fill)
    draw.ellipse([x2 - 2*radius, y2 - 2*radius, x2, y2], fill=fill)
    if outline:
        draw.arc([x1, y1, x1 + 2*radius, y1 + 2*radius], 180, 270, fill=outline)
        draw.arc([x2 - 2*radius, y1, x2, y1 + 2*radius], 270, 360, fill=outline)
        draw.arc([x1, y2 - 2*radius, x1 + 2*radius, y2], 90, 180, fill=outline)
        draw.arc([x2 - 2*radius, y2 - 2*radius, x2, y2], 0, 90, fill=outline)


def make_gradient(width: int, height: int, top_color: tuple, bottom_color: tuple) -> "Image.Image":
    """세로 방향 그라디언트 배경 이미지 생성"""
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        ratio = y / height
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * ratio)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * ratio)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    return img


# ─── 썸네일 생성 (1200×630) ───────────────────────────────────────────────────

def create_thumbnail(post: dict, output_path: str) -> bool:
    """OG 썸네일 이미지 생성 (1200×630)
    
    Args:
        post: 포스트 메타 데이터 (title, primary_keyword, domain, date 등)
        output_path: 저장 경로
    
    Returns:
        성공 여부
    """
    if not PIL_OK:
        print(f"  [thumbnail] ⚠ Pillow 없음 — 스킵")
        return False

    W, H = 1200, 630
    MARGIN = 60

    # 배경 그라디언트: 딥블루 → 다크퍼플
    top_col    = hex_to_rgb("#0d1b2a")
    bottom_col = hex_to_rgb("#1a0a2e")
    img = make_gradient(W, H, top_col, bottom_col)
    draw = ImageDraw.Draw(img)

    # 도메인 배지 색상
    domain = post.get("domain", "default")
    badge_hex = DOMAIN_COLORS.get(domain, DOMAIN_COLORS["default"])
    badge_color = hex_to_rgb(badge_hex)

    # ── 상단 좌측 카테고리 배지 ──────────────────────────────────────────────
    badge_font = load_font(22, bold=True)
    badge_text = domain
    try:
        bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
        btw = bbox[2] - bbox[0]
    except Exception:
        btw = len(badge_text) * 14
    bpad = 16
    bx1, by1 = MARGIN, 50
    bx2, by2 = bx1 + btw + bpad * 2, by1 + 38
    draw_rounded_rect(draw, (bx1, by1, bx2, by2), 8, badge_color)
    draw.text((bx1 + bpad, by1 + 7), badge_text, font=badge_font, fill=(255, 255, 255))

    # ── 중앙 제목 ────────────────────────────────────────────────────────────
    title = post.get("title", "제목 없음")
    title_font = load_font(56, bold=True)
    title_max_w = W - MARGIN * 2
    lines = smart_wrap(title, title_font, title_max_w, draw, max_lines=3)

    # 줄 높이 계산
    try:
        sample_bbox = draw.textbbox((0, 0), "가Ag", font=title_font)
        line_h = sample_bbox[3] - sample_bbox[1] + 14
    except Exception:
        line_h = 70
    total_text_h = line_h * len(lines)
    text_start_y = (H - total_text_h) // 2 - 20   # 약간 위로

    for i, line in enumerate(lines):
        draw.text((MARGIN, text_start_y + i * line_h), line, font=title_font, fill=(255, 255, 255))

    # ── 하단 네온 바 (키워드 태그) ───────────────────────────────────────────
    bar_h = 52
    bar_y = H - bar_h - 70
    neon_color = hex_to_rgb("#00d4ff")
    draw.rectangle([(0, bar_y), (W, bar_y + bar_h)], fill=(*neon_color, 220))

    # 키워드 태그
    kw_font = load_font(22, bold=True)
    keywords = [post.get("primary_keyword", "")] + post.get("secondary_keywords", [])[:3]
    kw_text = "  ·  ".join(f"#{kw}" for kw in keywords if kw)
    draw.text((MARGIN, bar_y + 14), kw_text, font=kw_font, fill=(10, 10, 10))

    # ── 하단 정보 (날짜 / 블로그명) ──────────────────────────────────────────
    footer_font = load_font(24)
    date_str = post.get("date", TODAY)
    draw.text((MARGIN, H - 55), date_str, font=footer_font, fill=(180, 180, 210))

    blog_name = "AI 인사이트 블로그"
    try:
        bn_bbox = draw.textbbox((0, 0), blog_name, font=footer_font)
        bn_w = bn_bbox[2] - bn_bbox[0]
    except Exception:
        bn_w = len(blog_name) * 15
    draw.text((W - MARGIN - bn_w, H - 55), blog_name, font=footer_font, fill=(180, 180, 210))

    # 저장
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG", optimize=True)
    print(f"  [thumbnail] 저장: {output_path}")
    return True


# ─── 인스타그램 카드 생성 (1080×1080) ────────────────────────────────────────

def create_instagram_card(post: dict, output_path: str) -> bool:
    """인스타그램 카드 이미지 생성 (1080×1080) — blog-writer 방식
    
    Args:
        post: 포스트 메타 데이터 (title, key_points, domain 등)
        output_path: 저장 경로
    
    Returns:
        성공 여부
    """
    if not PIL_OK:
        print(f"  [card] ⚠ Pillow 없음 — 스킵")
        return False

    W, H = 1080, 1080
    MARGIN = 70
    GOLD = hex_to_rgb("#c9a227")
    BAR_H = 10

    # 배경: 딥다크
    img = Image.new("RGB", (W, H), hex_to_rgb("#0a0a0a"))
    draw = ImageDraw.Draw(img)

    # ── 상단 금색 바 ─────────────────────────────────────────────────────────
    draw.rectangle([(0, 0), (W, BAR_H)], fill=GOLD)

    # ── 도메인 배지 ──────────────────────────────────────────────────────────
    domain = post.get("domain", "default")
    badge_hex = DOMAIN_COLORS.get(domain, DOMAIN_COLORS["default"])
    badge_color = hex_to_rgb(badge_hex)
    badge_font = load_font(24, bold=True)
    badge_text = domain
    try:
        bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
        btw = bbox[2] - bbox[0]
    except Exception:
        btw = len(badge_text) * 15
    bpad = 20
    center_x = W // 2
    bw = btw + bpad * 2
    bx1 = center_x - bw // 2
    bx2 = bx1 + bw
    by1, by2 = 40, 86
    draw_rounded_rect(draw, (bx1, by1, bx2, by2), 10, badge_color)
    draw.text((bx1 + bpad, by1 + 8), badge_text, font=badge_font, fill=(255, 255, 255))

    # ── 구분선 (금색) ────────────────────────────────────────────────────────
    draw.rectangle([(MARGIN, 105), (W - MARGIN, 107)], fill=(*GOLD, 180))

    # ── 제목 (중앙 정렬) ─────────────────────────────────────────────────────
    title = post.get("title", "제목 없음")
    title_font = load_font(52, bold=True)
    title_max_w = W - MARGIN * 2
    title_lines = smart_wrap(title, title_font, title_max_w, draw, max_lines=3)

    try:
        sample_bbox = draw.textbbox((0, 0), "가Ag", font=title_font)
        title_line_h = sample_bbox[3] - sample_bbox[1] + 12
    except Exception:
        title_line_h = 65

    title_y = 130
    for i, line in enumerate(title_lines):
        try:
            bbox = draw.textbbox((0, 0), line, font=title_font)
            lw = bbox[2] - bbox[0]
        except Exception:
            lw = len(line) * 33
        x = (W - lw) // 2
        draw.text((x, title_y + i * title_line_h), line, font=title_font, fill=(255, 255, 255))

    # ── 구분선 ───────────────────────────────────────────────────────────────
    sep_y = title_y + len(title_lines) * title_line_h + 30
    draw.rectangle([(MARGIN, sep_y), (W - MARGIN, sep_y + 2)], fill=(60, 60, 60))

    # ── 핵심 포인트 (3개) ────────────────────────────────────────────────────
    key_points = post.get("key_points", [])[:3]
    point_font = load_font(34)
    point_line_h = 44
    point_y = sep_y + 40
    point_color = (220, 220, 230)
    bullet_color = GOLD

    for pt in key_points:
        # 불릿 (•)
        draw.text((MARGIN, point_y), "•", font=point_font, fill=bullet_color)
        # 텍스트 줄바꿈
        pt_lines = smart_wrap(pt, point_font, W - MARGIN * 2 - 30, draw, max_lines=2)
        for j, pl in enumerate(pt_lines):
            draw.text((MARGIN + 30, point_y + j * point_line_h), pl, font=point_font, fill=point_color)
        point_y += point_line_h * len(pt_lines) + 18

    # ── 하단 금색 바 + URL ───────────────────────────────────────────────────
    footer_bar_y = H - 70
    draw.rectangle([(0, footer_bar_y), (W, H)], fill=GOLD)
    url_font = load_font(26, bold=True)
    blog_url = "ai-insight.blogspot.com"
    try:
        url_bbox = draw.textbbox((0, 0), blog_url, font=url_font)
        url_w = url_bbox[2] - url_bbox[0]
    except Exception:
        url_w = len(blog_url) * 16
    url_x = (W - url_w) // 2
    draw.text((url_x, footer_bar_y + 20), blog_url, font=url_font, fill=(10, 10, 10))

    # 저장
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG", optimize=True)
    print(f"  [card] 저장: {output_path}")
    return True


# ─── HTML 이미지 자리 교체 ────────────────────────────────────────────────────

def update_html_with_images(html_path: str, thumbnail_path: str) -> bool:
    """<!-- IMAGE: 설명 --> 주석 다음 figure 태그의 src를 실제 이미지 경로로 교체
    
    Args:
        html_path: HTML 파일 절대 경로
        thumbnail_path: 썸네일 이미지 절대 경로
    
    Returns:
        교체 성공 여부
    """
    if not os.path.exists(html_path):
        print(f"  [html] ⚠ HTML 파일 없음: {html_path}")
        return False

    # 상대 경로 계산 (HTML 파일 기준)
    html_dir = os.path.dirname(html_path)
    try:
        rel_path = os.path.relpath(thumbnail_path, html_dir)
    except ValueError:
        rel_path = thumbnail_path  # Windows 드라이브 다른 경우 절대 경로 사용

    content = open(html_path, encoding="utf-8").read()

    # <!-- IMAGE: ... --> 주석 직후 figure > img src 교체
    # 패턴: <!-- IMAGE: ... -->\n<figure>...<img ...src="placeholder..."...>
    pattern = r'(<!-- IMAGE:[^>]*-->[\s\S]*?<img[^>]+)src="[^"]*"'
    replacement = rf'\1src="{rel_path}"'
    new_content, count = re.subn(pattern, replacement, content, count=1)

    if count == 0:
        # figure 태그만 있는 경우도 시도
        pattern2 = r'(<figure[^>]*>[\s\S]*?<img[^>]+)src="placeholder[^"]*"'
        new_content, count = re.subn(pattern2, replacement, content, count=1)

    if count > 0:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"  [html] 이미지 src 교체: {rel_path}")
        return True
    else:
        print(f"  [html] ⚠ 교체 대상 figure/img 태그 미발견")
        return False


# ─── ImgBB 업로드 ────────────────────────────────────────────────────────────

def upload_to_imgbb(image_path: str) -> str:
    """ImgBB API로 이미지 업로드 후 공개 URL 반환
    
    환경변수 IMGBB_API_KEY 필요. 없으면 빈 문자열 반환.
    
    Args:
        image_path: 업로드할 이미지 파일 경로
    
    Returns:
        공개 URL 또는 "" (실패/키 없음)
    """
    api_key = os.environ.get("IMGBB_API_KEY", "")
    if not api_key:
        return ""
    if not REQUESTS_OK:
        print("  [imgbb] ⚠ requests 미설치")
        return ""
    if not os.path.exists(image_path):
        return ""

    try:
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        resp = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": api_key, "image": img_b64},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        url = data["data"]["url"]
        print(f"  [imgbb] 업로드 성공: {url}")
        return url
    except Exception as e:
        print(f"  [imgbb] 업로드 실패: {e}")
        return ""


# ─── 메인 run() ──────────────────────────────────────────────────────────────

def run(write_data: dict = None) -> dict:
    """이미지 생성 에이전트 메인 진입점
    
    Args:
        write_data: Writer 에이전트 출력 (없으면 write_log_TODAY.json 로드)
    
    Returns:
        {
            "date": ...,
            "images_generated": N,
            "posts": [
                {
                    "post_num": 1,
                    "thumbnail": "output/images/..._thumb.png",
                    "card": "output/images/..._card.png",
                    "thumbnail_url": "",  # ImgBB URL (키 있을 때)
                    "html_updated": True/False,
                }
            ]
        }
    """
    print("[image_gen] 이미지 생성 에이전트 시작")

    if not PIL_OK:
        print("[image_gen] ⚠ Pillow 없음 — 이미지 생성 불가. pip install Pillow")
        return {"error": "Pillow not installed", "images_generated": 0}

    # write_data 로드
    if write_data is None:
        log_path = os.path.join(BASE, "output", "logs", f"write_log_{TODAY}.json")
        if os.path.exists(log_path):
            with open(log_path, encoding="utf-8") as f:
                write_data = json.load(f)
            print(f"  write_log 로드: {log_path}")
        else:
            print(f"  ⚠ write_log 없음: {log_path}")
            write_data = {"date": TODAY, "posts": []}

    date_str = write_data.get("date", TODAY)
    posts = write_data.get("posts", [])

    OUT_IMG_DIR = os.path.join(BASE, "output", "images")
    OUT_POST_DIR = os.path.join(BASE, "output", "posts")
    os.makedirs(OUT_IMG_DIR, exist_ok=True)

    results = []
    generated = 0

    for post in posts:
        post_num = post.get("post_num", 1)
        title = post.get("title", "제목 없음")
        print(f"\n  [포스트 {post_num}] {title[:40]}...")

        # 포스트에 날짜 주입
        post_with_date = {**post, "date": date_str}

        # 파일명
        thumb_name = f"post_{date_str}_{post_num}_thumb.png"
        card_name  = f"post_{date_str}_{post_num}_card.png"
        thumb_path = os.path.join(OUT_IMG_DIR, thumb_name)
        card_path  = os.path.join(OUT_IMG_DIR, card_name)

        # 썸네일 생성
        thumb_ok = create_thumbnail(post_with_date, thumb_path)

        # 인스타그램 카드 생성
        card_ok = create_instagram_card(post_with_date, card_path)

        if thumb_ok or card_ok:
            generated += 1

        # HTML 이미지 자리 교체
        html_file = post.get("html_file", f"post_{date_str}_{post_num}.html")
        html_path = os.path.join(OUT_POST_DIR, html_file)
        html_updated = False
        if thumb_ok and os.path.exists(html_path):
            html_updated = update_html_with_images(html_path, thumb_path)

        # ImgBB 업로드 (썸네일)
        thumb_url = ""
        if thumb_ok:
            thumb_url = upload_to_imgbb(thumb_path)

        results.append({
            "post_num":      post_num,
            "title":         title,
            "thumbnail":     thumb_path if thumb_ok else "",
            "card":          card_path if card_ok else "",
            "thumbnail_url": thumb_url,
            "html_updated":  html_updated,
        })

    # 결과 로그 저장
    result_data = {
        "date":             date_str,
        "images_generated": generated,
        "posts":            results,
    }
    log_out = os.path.join(BASE, "output", "logs", f"image_log_{date_str}.json")
    os.makedirs(os.path.dirname(log_out), exist_ok=True)
    with open(log_out, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    print(f"\n[image_gen] 완료 — {generated}개 포스트 이미지 생성 → {log_out}")
    return result_data


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, ensure_ascii=False, indent=2))
