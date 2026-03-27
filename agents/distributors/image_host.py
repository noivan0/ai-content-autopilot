"""
이미지 호스팅 헬퍼 — P004 버전 (agents/distributors/image_host.py)
역할: 로컬 카드 이미지 → 공개 URL 변환

지원 방식:
1. ImgBB (무료 API, 키 필요)   ← IMGBB_API_KEY 설정 시
2. 로컬 HTTP 서버 (개발/테스트) ← LOCAL_IMAGE_SERVER=true 시

ref: sinmb79/blog-writer bots/distributors/image_host.py
"""
import base64
import logging
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
LOG_DIR = BASE_DIR / 'output' / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.FileHandler(LOG_DIR / 'distributor.log', encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)

IMGBB_API_KEY = os.getenv('IMGBB_API_KEY', '')
IMGBB_API_URL = 'https://api.imgbb.com/v1/upload'


def upload_to_imgbb(image_path: str, expiration: int = 0) -> str:
    """
    ImgBB에 이미지 업로드.
    expiration: 0=영구, 초 단위 (예: 86400=1일)
    Returns: 공개 URL 또는 ''
    """
    if not IMGBB_API_KEY:
        logger.debug("IMGBB_API_KEY 없음 — ImgBB 건너뜀")
        return ''

    try:
        import requests
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        payload = {'key': IMGBB_API_KEY, 'image': image_data}
        if expiration > 0:
            payload['expiration'] = expiration

        resp = requests.post(IMGBB_API_URL, data=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        if result.get('success'):
            url = result['data']['url']
            logger.info(f"ImgBB 업로드 완료: {url}")
            return url
        else:
            logger.warning(f"ImgBB 오류: {result.get('error', {})}")
            return ''
    except Exception as e:
        logger.error(f"ImgBB 업로드 실패: {e}")
        return ''


_local_server = None


def start_local_server(port: int = 8765) -> str:
    """로컬 HTTP 파일 서버 시작 (개발용). Returns: base URL"""
    import socket
    import threading
    import http.server
    import functools

    global _local_server
    if _local_server:
        return _local_server

    outputs_dir = str(BASE_DIR / 'output' / 'images')
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=outputs_dir)
    server = http.server.HTTPServer(('0.0.0.0', port), handler)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = '127.0.0.1'

    base_url = f'http://{local_ip}:{port}'
    _local_server = base_url
    logger.info(f"로컬 이미지 서버 시작: {base_url}")
    return base_url


def get_local_url(image_path: str, port: int = 8765) -> str:
    """로컬 서버 URL 반환"""
    base_url = start_local_server(port)
    filename = Path(image_path).name
    return f'{base_url}/{filename}'


def get_public_url(image_path: str) -> str:
    """
    이미지 파일 → 공개 URL.
    우선순위: ImgBB → 로컬 서버(개발용)
    """
    if not Path(image_path).exists():
        logger.error(f"이미지 파일 없음: {image_path}")
        return ''

    # 1. ImgBB
    url = upload_to_imgbb(image_path, expiration=86400 * 7)  # 7일
    if url:
        return url

    # 2. 로컬 HTTP 서버 (ngrok 등으로 터널링 시)
    if os.getenv('LOCAL_IMAGE_SERVER', '').lower() == 'true':
        url = get_local_url(image_path)
        logger.warning(f"로컬 서버 URL 사용 (인터넷 접근 필요): {url}")
        return url

    logger.warning(
        "공개 URL 생성 불가. .env에 IMGBB_API_KEY를 설정하거나 "
        "LOCAL_IMAGE_SERVER=true로 설정하세요."
    )
    return ''


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        url = get_public_url(sys.argv[1])
        print(f"공개 URL: {url}")
    else:
        print("사용법: python image_host.py <이미지경로>")
