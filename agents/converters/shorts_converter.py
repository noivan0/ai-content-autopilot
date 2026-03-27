"""
쇼츠 변환봇 — P004 버전 (agents/converters/shorts_converter.py)
역할: article dict → 뉴스앵커 포맷 쇼츠 MP4
ffmpeg 없을 시 graceful skip.

출력: output/shorts/{date}_{slug}_shorts.mp4

ref: sinmb79/blog-writer bots/converters/shorts_converter.py
"""
import base64
import json
import logging
import os
import subprocess
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).parent.parent.parent
LOG_DIR = BASE_DIR / 'output' / 'logs'
OUTPUT_DIR = BASE_DIR / 'output' / 'shorts'
ASSETS_DIR = BASE_DIR / 'assets'
FONTS_DIR = ASSETS_DIR / 'fonts'
TEMPLATE_PATH = BASE_DIR / 'templates' / 'shorts_template.json'
BGM_PATH = ASSETS_DIR / 'bgm.mp3'

LOG_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.FileHandler(LOG_DIR / 'converter.log', encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)

FFMPEG = os.getenv('FFMPEG_PATH', 'ffmpeg')
FFPROBE = os.getenv('FFPROBE_PATH', 'ffprobe')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
GOOGLE_TTS_API_KEY = os.getenv('GOOGLE_TTS_API_KEY', '')

COLOR_DARK = (10, 10, 13)
COLOR_DARK2 = (15, 10, 30)
COLOR_BLUE = (59, 130, 246)       # P004 기본색
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)


def _load_template() -> dict:
    if TEMPLATE_PATH.exists():
        return json.loads(TEMPLATE_PATH.read_text(encoding='utf-8'))
    return {
        'brand_name': 'AI 인사이트',
        'brand_sub': '최신 AI 트렌드 분석',
        'brand_by': 'P004 Auto',
        'outro_url': 'ai-insight-blog.blogspot.com',
        'outro_cta': '구독하면 매일 AI 소식을 받습니다',
        'bgm_volume': 0.08,
        'tts_voice_ko': 'ko-KR-Wavenet-A',
        'tts_speaking_rate_default': 1.05,
        'transition_duration': 0.5,
        'font_title_size': 72,
        'font_body_size': 48,
        'font_meta_size': 32,
        'font_ticker_size': 28,
        'ticker_text': 'AI 인사이트 · {corner} · {date}',
        'corners': {},
    }


def _load_font(size: int, bold: bool = False):
    try:
        from PIL import ImageFont
        candidates = (
            ['NotoSansKR-Bold.ttf', 'NotoSansKR-Medium.ttf'] if bold
            else ['NotoSansKR-Regular.ttf', 'NotoSansKR-Medium.ttf']
        )
        for fname in candidates:
            p = FONTS_DIR / fname
            if p.exists():
                return ImageFont.truetype(str(p), size)
        for path in [
            '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            '/System/Library/Fonts/AppleSDGothicNeo.ttc',
            'C:/Windows/Fonts/malgunbd.ttf' if bold else 'C:/Windows/Fonts/malgun.ttf',
        ]:
            if Path(path).exists():
                return ImageFont.truetype(path, size)
        return ImageFont.load_default()
    except Exception:
        return None


def _text_size(draw, text: str, font) -> tuple:
    try:
        bb = draw.textbbox((0, 0), text, font=font)
        return bb[2] - bb[0], bb[3] - bb[1]
    except AttributeError:
        return draw.textsize(text, font=font)


def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _draw_rounded_rect(draw, xy, radius: int, fill):
    x1, y1, x2, y2 = xy
    r = radius
    draw.rectangle([x1 + r, y1, x2 - r, y2], fill=fill)
    draw.rectangle([x1, y1 + r, x2, y2 - r], fill=fill)
    for cx, cy in [(x1, y1), (x2 - 2*r, y1), (x1, y2 - 2*r), (x2 - 2*r, y2 - 2*r)]:
        draw.ellipse([cx, cy, cx + 2*r, cy + 2*r], fill=fill)


def _wrap_text_lines(text: str, font, max_width: int, draw) -> list:
    words = text.split()
    lines = []
    current = ''
    for word in words:
        test = (current + ' ' + word).strip()
        w, _ = _text_size(draw, test, font)
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _check_ffmpeg() -> bool:
    try:
        r = subprocess.run([FFMPEG, '-version'], capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


def _run_ffmpeg(args: list, quiet: bool = False) -> bool:
    cmd = [FFMPEG, '-y'] + ((['-loglevel', 'error'] if quiet else []) + args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.error(f"ffmpeg 오류: {result.stderr[-400:]}")
        return result.returncode == 0
    except Exception as e:
        logger.error(f"ffmpeg 실행 오류: {e}")
        return False


def _tts_google_rest(text: str, output_path: str, voice: str, speed: float) -> bool:
    if not GOOGLE_TTS_API_KEY:
        return False
    try:
        import requests as req
        url = f'https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_TTS_API_KEY}'
        lang = 'ko-KR' if voice.startswith('ko') else 'en-US'
        payload = {
            'input': {'text': text},
            'voice': {'languageCode': lang, 'name': voice},
            'audioConfig': {'audioEncoding': 'LINEAR16', 'speakingRate': speed, 'pitch': 0},
        }
        resp = req.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        audio_b64 = resp.json().get('audioContent', '')
        if audio_b64:
            Path(output_path).write_bytes(base64.b64decode(audio_b64))
            return True
    except Exception as e:
        logger.warning(f"Google Cloud TTS 실패: {e}")
    return False


def _tts_gtts(text: str, output_path: str) -> bool:
    try:
        from gtts import gTTS
        mp3_path = output_path.replace('.wav', '_tmp.mp3')
        tts = gTTS(text=text, lang='ko', slow=False)
        tts.save(mp3_path)
        _run_ffmpeg(['-i', mp3_path, '-ar', '24000', output_path], quiet=True)
        Path(mp3_path).unlink(missing_ok=True)
        return Path(output_path).exists()
    except Exception as e:
        logger.warning(f"gTTS 실패: {e}")
    return False


def synthesize_section(text: str, output_path: str, voice: str, speed: float) -> bool:
    if _tts_google_rest(text, output_path, voice, speed):
        return True
    return _tts_gtts(text, output_path)


def get_audio_duration(wav_path: str) -> float:
    try:
        result = subprocess.run(
            [FFPROBE, '-v', 'quiet', '-print_format', 'json', '-show_format', wav_path],
            capture_output=True, text=True, timeout=10
        )
        data = json.loads(result.stdout)
        return float(data['format']['duration'])
    except Exception:
        return 5.0


_tmp_dir: Optional[Path] = None

def _set_tmp_dir(d: Path):
    global _tmp_dir
    _tmp_dir = d

def _tmp_slide(name: str) -> Path:
    return _tmp_dir / f'slide_{name}.png'

def _tmp_wav(name: str) -> Path:
    return _tmp_dir / f'tts_{name}.wav'

def _tmp_clip(name: str) -> Path:
    return _tmp_dir / f'clip_{name}.mp4'


def compose_intro_slide(cfg: dict) -> str:
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (1080, 1920), COLOR_DARK)
    draw = ImageDraw.Draw(img)
    W, H = 1080, 1920
    draw.rectangle([60, H//3 - 2, W - 60, H//3], fill=COLOR_BLUE)
    font_brand = _load_font(cfg.get('font_title_size', 72), bold=True)
    font_sub = _load_font(cfg.get('font_body_size', 48))
    font_meta = _load_font(cfg.get('font_meta_size', 32))
    brand = cfg.get('brand_name', 'AI 인사이트')
    sub = cfg.get('brand_sub', '최신 AI 트렌드 분석')
    by_text = cfg.get('brand_by', 'P004 Auto')
    bh = 72
    if font_brand:
        bw, bh = _text_size(draw, brand, font_brand)
        draw.text(((W - bw) // 2, H // 3 + 60), brand, font=font_brand, fill=COLOR_BLUE)
    if font_sub:
        sw, sh = _text_size(draw, sub, font_sub)
        draw.text(((W - sw) // 2, H // 3 + 60 + bh + 24), sub, font=font_sub, fill=COLOR_WHITE)
    if font_meta:
        mw, mh = _text_size(draw, by_text, font_meta)
        draw.text(((W - mw) // 2, H * 2 // 3), by_text, font=font_meta, fill=COLOR_BLUE)
    path = str(_tmp_slide('intro'))
    img.save(path)
    return path


def compose_headline_slide(article: dict, cfg: dict, bg_img=None) -> str:
    from PIL import Image, ImageDraw
    corner = article.get('corner', 'AI 인사이트')
    corner_cfg = cfg.get('corners', {}).get(corner, {})
    corner_color = _hex_to_rgb(corner_cfg.get('color', '#3b82f6'))
    if bg_img is None:
        bg_img = Image.new('RGB', (1080, 1920), (20, 20, 35))
    img = bg_img.copy()
    draw = ImageDraw.Draw(img)
    W, H = 1080, 1920
    font_badge = _load_font(36)
    font_title = _load_font(cfg.get('font_title_size', 72), bold=True)
    font_meta = _load_font(cfg.get('font_meta_size', 32))
    _draw_rounded_rect(draw, [60, 120, 60 + len(corner) * 28 + 40, 190], 20, corner_color)
    if font_badge:
        draw.text((80, 133), corner, font=font_badge, fill=COLOR_WHITE)
    title = article.get('title', '')
    if font_title:
        lines = _wrap_text_lines(title, font_title, W - 120, draw)[:3]
        y = H // 2 - (len(lines) * 90) // 2
        for line in lines:
            draw.text((60, y), line, font=font_title, fill=COLOR_WHITE)
            y += 90
    meta_text = f"{datetime.now().strftime('%Y.%m.%d')}  ·  P004 AI 인사이트"
    if font_meta:
        draw.text((60, H - 160), meta_text, font=font_meta, fill=COLOR_BLUE)
    draw.rectangle([0, H - 100, W, H - 96], fill=COLOR_BLUE)
    path = str(_tmp_slide('headline'))
    img.save(path)
    return path


def compose_point_slide(point: str, num: int, article: dict, cfg: dict, bg_img=None) -> str:
    from PIL import Image, ImageDraw, ImageEnhance
    corner = article.get('corner', 'AI 인사이트')
    corner_cfg = cfg.get('corners', {}).get(corner, {})
    corner_color = _hex_to_rgb(corner_cfg.get('color', '#3b82f6'))
    if bg_img is None:
        bg_img = Image.new('RGB', (1080, 1920), (20, 15, 35))
    img = ImageEnhance.Brightness(bg_img.copy()).enhance(0.4)
    draw = ImageDraw.Draw(img)
    W, H = 1080, 1920
    font_num = _load_font(80, bold=True)
    font_point = _load_font(cfg.get('font_body_size', 48))
    font_ticker = _load_font(cfg.get('font_ticker_size', 28))
    badges = ['①', '②', '③']
    badge_char = badges[num - 1] if num <= 3 else str(num)
    if font_num:
        draw.ellipse([60, 160, 200, 300], fill=corner_color)
        bw, bh = _text_size(draw, badge_char, font_num)
        draw.text((60 + (140 - bw) // 2, 160 + (140 - bh) // 2), badge_char, font=font_num, fill=COLOR_WHITE)
    if font_point:
        lines = _wrap_text_lines(point, font_point, W - 120, draw)[:4]
        y = H // 2 - (len(lines) * 70) // 2
        for line in lines:
            draw.text((60, y), line, font=font_point, fill=COLOR_WHITE)
            y += 70
    ticker_text = cfg.get('ticker_text', 'AI 인사이트 · {corner} · {date}')
    ticker_text = ticker_text.format(corner=corner, date=datetime.now().strftime('%Y.%m.%d'))
    draw.rectangle([0, H - 100, W, H], fill=COLOR_BLACK)
    if font_ticker:
        draw.text((30, H - 78), ticker_text, font=font_ticker, fill=COLOR_BLUE)
    path = str(_tmp_slide(f'point{num}'))
    img.save(path)
    return path


def compose_outro_slide(cfg: dict) -> str:
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (1080, 1920), COLOR_DARK)
    draw = ImageDraw.Draw(img)
    W, H = 1080, 1920
    draw.rectangle([60, H // 3, W - 60, H // 3 + 4], fill=COLOR_BLUE)
    draw.rectangle([60, H * 2 // 3 + 80, W - 60, H * 2 // 3 + 84], fill=COLOR_BLUE)
    font_brand = _load_font(64, bold=True)
    font_cta = _load_font(48)
    font_url = _load_font(52, bold=True)
    font_sub = _load_font(36)
    url = cfg.get('outro_url', 'ai-insight-blog.blogspot.com')
    follow = cfg.get('outro_cta', '구독하면 매일 AI 소식을 받습니다')
    brand = cfg.get('brand_name', 'AI 인사이트')
    y = H // 3 + 60
    for text, font, color in [
        ('더 자세한 내용은', font_cta, COLOR_WHITE),
        (url, font_url, COLOR_BLUE),
        ('', None, None),
        (brand, font_brand, COLOR_WHITE),
        (follow, font_sub, (180, 180, 180)),
    ]:
        if not font:
            y += 40
            continue
        tw, th = _text_size(draw, text, font)
        draw.text(((W - tw) // 2, y), text, font=font, fill=color)
        y += th + 24
    path = str(_tmp_slide('outro'))
    img.save(path)
    return path


def make_clip(slide_png: str, audio_wav: str, output_mp4: str) -> float:
    duration = get_audio_duration(audio_wav) + 0.3
    ok = _run_ffmpeg([
        '-loop', '1', '-i', slide_png,
        '-i', audio_wav,
        '-c:v', 'libx264', '-tune', 'stillimage',
        '-c:a', 'aac', '-b:a', '192k',
        '-pix_fmt', 'yuv420p',
        '-vf', 'scale=1080:1920,zoompan=z=\'min(zoom+0.0003,1.05)\':x=\'iw/2-(iw/zoom/2)\':y=\'ih/2-(ih/zoom/2)\':d=1:s=1080x1920:fps=30',
        '-shortest', '-r', '30', output_mp4,
    ], quiet=True)
    return duration if ok else 0.0


def concat_clips(clips: list, output_mp4: str) -> bool:
    if len(clips) == 1:
        import shutil
        shutil.copy2(clips[0]['mp4'], output_mp4)
        return True
    n = len(clips)
    inputs = []
    for c in clips:
        inputs += ['-i', c['mp4']]
    filter_parts = []
    prev_v = '[0:v]'
    prev_a = '[0:a]'
    trans_dur = 0.5
    for i in range(1, n):
        offset = sum(c['duration'] for c in clips[:i]) - trans_dur * i
        out_v = f'[f{i}v]' if i < n - 1 else '[video]'
        out_a = f'[f{i}a]' if i < n - 1 else '[audio]'
        filter_parts.append(f'{prev_v}[{i}:v]xfade=transition=fade:duration={trans_dur}:offset={offset:.3f}{out_v}')
        filter_parts.append(f'{prev_a}[{i}:a]acrossfade=d={trans_dur}{out_a}')
        prev_v = out_v
        prev_a = out_a
    filter_complex = '; '.join(filter_parts)
    return _run_ffmpeg(inputs + [
        '-filter_complex', filter_complex,
        '-map', '[video]', '-map', '[audio]',
        '-c:v', 'libx264', '-c:a', 'aac', '-pix_fmt', 'yuv420p', output_mp4,
    ])


class ShortsConverter:
    def __init__(self):
        self.cfg = _load_template()

    def generate(self, article: dict) -> str:
        """메인 파이프라인. ffmpeg 없으면 '' 반환 (graceful)"""
        import tempfile

        if not _check_ffmpeg():
            logger.warning("ffmpeg 없음 — 쇼츠 생성 건너뜀 (PATH 또는 FFMPEG_PATH 확인)")
            return ''

        key_points = article.get('key_points', [])
        if not key_points:
            logger.warning("key_points 없음 — 쇼츠 생성 불가")
            return ''

        title = article.get('title', '')
        corner = article.get('corner', 'AI 인사이트')
        slug = article.get('slug', 'article')
        date_str = datetime.now().strftime('%Y%m%d')

        corner_cfg = self.cfg.get('corners', {}).get(corner, {})
        tts_speed = corner_cfg.get('tts_speed', self.cfg.get('tts_speaking_rate_default', 1.05))
        voice = self.cfg.get('tts_voice_ko', 'ko-KR-Wavenet-A')

        logger.info(f"쇼츠 변환 시작: {title} / {corner}")

        try:
            with tempfile.TemporaryDirectory() as tmp:
                _set_tmp_dir(Path(tmp))

                title_short = title[:40] + ('...' if len(title) > 40 else '')
                scripts = {
                    'intro': f'오늘은 {title_short}에 대해 알아보겠습니다.',
                    'headline': title_short,
                }
                for i, kp in enumerate(key_points[:3], 1):
                    scripts[f'point{i}'] = str(kp)
                scripts['outro'] = (
                    f'자세한 내용은 {self.cfg.get("outro_url", "ai-insight-blog.blogspot.com")}에서 확인하세요. '
                    '구독 부탁드립니다.'
                )

                slides = {
                    'intro': compose_intro_slide(self.cfg),
                    'headline': compose_headline_slide(article, self.cfg),
                }
                for i, kp in enumerate(key_points[:3], 1):
                    slides[f'point{i}'] = compose_point_slide(str(kp), i, article, self.cfg)
                slides['outro'] = compose_outro_slide(self.cfg)

                clips = []
                for key in scripts:
                    wav_path = str(_tmp_wav(key))
                    clip_path = str(_tmp_clip(key))
                    slide_path = slides.get(key)
                    if not slide_path or not Path(slide_path).exists():
                        continue
                    ok = synthesize_section(scripts[key], wav_path, voice, tts_speed)
                    if not ok:
                        _run_ffmpeg(['-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono', '-t', '2', wav_path], quiet=True)
                    dur = make_clip(slide_path, wav_path, clip_path)
                    if dur > 0:
                        clips.append({'mp4': clip_path, 'duration': dur})

                if not clips:
                    logger.error("생성된 클립 없음")
                    return ''

                merged = str(Path(tmp) / 'merged.mp4')
                if not concat_clips(clips, merged):
                    return ''

                output_path = str(OUTPUT_DIR / f'{date_str}_{slug}_shorts.mp4')
                # BGM 믹스 (파일 없으면 바로 복사)
                if BGM_PATH.exists():
                    vol = self.cfg.get('bgm_volume', 0.08)
                    with_bgm = str(Path(tmp) / 'with_bgm.mp4')
                    ok = _run_ffmpeg([
                        '-i', merged, '-i', str(BGM_PATH),
                        '-filter_complex', f'[1:a]volume={vol}[bgm];[0:a][bgm]amix=inputs=2:duration=first[a]',
                        '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-shortest', with_bgm,
                    ])
                    import shutil
                    shutil.copy2(with_bgm if ok and Path(with_bgm).exists() else merged, output_path)
                else:
                    import shutil
                    shutil.copy2(merged, output_path)

        except Exception as e:
            logger.error(f"쇼츠 생성 오류: {e}")
            return ''

        logger.info(f"쇼츠 생성 완료: {output_path}")
        return output_path


def convert(article: dict, card_path: str = '', save_file: bool = True) -> str:
    """진입점 함수 (graceful: ffmpeg 없으면 '' 반환)"""
    sc = ShortsConverter()
    return sc.generate(article)


if __name__ == '__main__':
    sample = {
        'title': 'ChatGPT o3 완벽 분석',
        'slug': 'chatgpt-o3-test',
        'corner': 'AI 소식',
        'key_points': ['o3는 수학·코딩에서 인간 전문가 수준', 'API 비용 GPT-4o 대비 6배', '멀티모달 지원'],
    }
    path = convert(sample)
    print(f'완료: {path}')
